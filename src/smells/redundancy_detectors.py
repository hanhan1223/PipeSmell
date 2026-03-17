"""
冗余类Smell检测器模块

提供针对Pipeline冗余问题的检测器，包括重复数据转换、不必要数据复制和冗余操作。
所有检测器都继承自SmellDetector基类，实现冗余相关的检测逻辑。
"""

from collections import defaultdict
from typing import Any, Dict, List

from src.core.pipeline import PipelineGraph, PipelineNode
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    EXCESSIVE_COPY,
    REDUNDANT_OPERATION,
    REPEATED_TRANSFORM,
    SeverityLevel,
)


class RepeatedTransformDetector(SmellDetector):
    """重复数据转换检测器
    
    检测对同一数据变量多次执行相同类型的转换操作，造成不必要的重复计算。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义可转换操作的分类
        self.transform_operations = {
            'fillna': 'NaN填充',
            'dropna': 'NaN删除',
            'drop': '列删除',
            'replace': '值替换',
            'fillna': '填充操作',
            'str.lower': '小写转换',
            'str.upper': '大写转换',
            'str.strip': '字符串修剪',
            'astype': '类型转换',
            'astype_': '类型转换',
            'str.replace': '字符串替换',
        }
        self.logger.info("RepeatedTransformDetector初始化完成")
    
    def detect(self, pipeline_graph: PipelineGraph, 
               module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的重复数据转换操作
        
        按操作类型分组Pipeline nodes，识别对同一组变量（inputs匹配）
        执行多次相同转换的情况。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序
            
        Returns:
            检测到的Smell实例列表，每个实例代表一处重复转换问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells
        
        # 按操作类型和输入变量分组
        transform_groups = defaultdict(list)
        
        for node in nodes:
            operation_key = self._get_operation_key(node.api_name)
            if operation_key:
                # 使用输入变量列表的元组作为分组键
                input_key = tuple(sorted(node.inputs)) if node.inputs else ()
                group_key = (operation_key, input_key)
                transform_groups[group_key].append(node)
        
        self.logger.debug(f"找到 {len(transform_groups)} 个转换操作组")
        
        # 检查每组中是否有多于1个转换操作
        for (operation_key, input_key), group_nodes in transform_groups.items():
            if len(group_nodes) >= 2:
                # 发现重复转换
                # 检查这些操作之间是否有其他改变数据状态的操作
                if self._is_repeated_transform_valid(group_nodes, nodes):
                    smell_instance = self._create_repeated_transform_smell(
                        operation_key=operation_key,
                        input_vars=list(input_key) if input_key else [],
                        nodes=group_nodes
                    )
                    detected_smells.append(smell_instance)
                    self.logger.warning(
                        f"检测到重复转换: {operation_key} 在 {len(group_nodes)} 个位置执行, "
                        f"输入变量: {', '.join(input_key) if input_key else 'N/A'}"
                    )
        
        self.logger.info(f"RepeatedTransform检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells
    
    def _get_operation_key(self, api_name: str) -> str:
        """获取API名称对应的操作类型键
        
        Args:
            api_name: API名称
            
        Returns:
            操作类型键，如果不是转换操作则返回None
        """
        for op_name, description in self.transform_operations.items():
            if op_name in api_name.lower():
                return op_name
        return None
    
    def _is_repeated_transform_valid(self, group_nodes: List[PipelineNode], 
                                    all_nodes: List[PipelineNode]) -> bool:
        """判断是否是真正的重复转换
        
        检查这些重复转换之间是否有其他改变数据状态的操作，
        如果没有则是真正的重复转换。
        
        Args:
            group_nodes: 同一组转换操作的节点列表
            all_nodes: 所有节点列表
            
        Returns:
            如果是真正的重复转换则返回True，否则返回False
        """
        if len(group_nodes) < 2:
            return False
        
        # 按行号排序
        sorted_group = sorted(group_nodes, key=lambda x: x.line_number)
        
        # 检查相邻的两个转换之间是否有修改操作
        for i in range(len(sorted_group) - 1):
            first_node = sorted_group[i]
            second_node = sorted_group[i + 1]
            
            # 查找两个节点之间的操作
            nodes_between = [
                node for node in all_nodes
                if first_node.line_number < node.line_number < second_node.line_number
            ]
            
            # 检查中间是否只有数据读取或辅助操作
            has_modifying_operation = any(
                self._is_modifying_operation(node.api_name)
                for node in nodes_between
            )
            
            # 如果没有修改操作，则认为是重复转换
            if not has_modifying_operation:
                return True
        
        return False
    
    def _is_modifying_operation(self, api_name: str) -> bool:
        """判断操作是否会修改数据
        
        Args:
            api_name: API名称
            
        Returns:
            如果操作会修改数据则返回True
        """
        modifying_keywords = ['fit', 'transform', 'predict', 'train', 'drop', 
                            'fillna', 'replace', 'append', 'concat', 'merge']
        return any(keyword in api_name.lower() for keyword in modifying_keywords)
    
    def _create_repeated_transform_smell(self, operation_key: str, 
                                        input_vars: List[str],
                                        nodes: List[PipelineNode]) -> SmellInstance:
        """创建重复转换的Smell实例
        
        Args:
            operation_key: 操作类型键
            input_vars: 输入变量列表
            nodes: 重复转换的节点列表
            
        Returns:
            SmellInstance对象
        """
        # 使用第一个节点作为主要位置
        first_node = min(nodes, key=lambda x: x.line_number)
        
        location = LocationInfo(
            file_path=first_node.location,
            line_number=first_node.line_number,
            code_snippet=first_node.code_snippet
        )
        
        input_str = ', '.join(input_vars) if input_vars else '未指定变量'
        positions = ', '.join(f"第{node.line_number}行" for node in nodes)
        
        description = (
            f"检测到重复数据转换: 对变量 {{{input_str}}} 执行了多次 '{operation_key}' 操作，"
            f"分别在 {positions}。这造成不必要的重复计算，增加计算开销，降低代码可维护性。"
        )
        
        suggestion = (
            f"建议移除重复的转换操作，保留第一次 {operation_key} 即可。"
            f"如果需要多次转换，请检查是否存在逻辑错误或数据流转问题。"
        )
        
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.MEDIUM.value,
            affected_nodes=[node.node_id for node in nodes],
            suggestion=suggestion
        )
    
    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的Pipeline节点列表
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按line_number升序排序的PipelineNode列表
        """
        nodes_data = []
        
        for node_id in pipeline_graph.graph.nodes():
            node_data = pipeline_graph.graph.nodes[node_id]
            
            pipeline_node = PipelineNode(
                node_id=node_id,
                operation_type=node_data.get('operation_type'),
                api_name=node_data.get('api_name', ''),
                inputs=node_data.get('inputs', []),
                outputs=node_data.get('outputs', []),
                line_number=node_data.get('line_number', 0),
                code_snippet=node_data.get('code_snippet', ''),
                location=node_data.get('location', ''),
                attributes=node_data.get('attributes', {})
            )
            nodes_data.append(pipeline_node)
        
        sorted_nodes = sorted(nodes_data, key=lambda x: x.line_number)
        return sorted_nodes


class ExcessiveCopyDetector(SmellDetector):
    """不必要数据复制检测器
    
    检测在不必要的情况下对DataFrame进行复制操作，增加内存占用和计算开销。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("ExcessiveCopyDetector初始化完成")
    
    def detect(self, pipeline_graph: PipelineGraph, 
               module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的不必要数据复制操作
        
        检查DataFrame.copy()调用，分析后续操作是否真正需要副本。
        若副本后无修改或原数据未被使用则标记为excessive。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序
            
        Returns:
            检测到的Smell实例列表，每个实例代表一处过度复制问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells
        
        # 查找所有copy操作节点
        copy_nodes = [
            node for node in nodes 
            if self._is_copy_operation(node.api_name)
        ]
        
        self.logger.debug(f"找到 {len(copy_nodes)} 个copy操作节点")
        
        # 检查每个copy操作是否必要
        for copy_node in copy_nodes:
            if self._is_excessive_copy(copy_node, nodes):
                smell_instance = self._create_excessive_copy_smell(copy_node)
                detected_smells.append(smell_instance)
                self.logger.warning(
                    f"检测到不必要的数据复制: {copy_node.api_name} 在第 {copy_node.line_number} 行"
                )
        
        self.logger.info(f"ExcessiveCopy检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells
    
    def _is_copy_operation(self, api_name: str) -> bool:
        """判断是否是copy操作
        
        Args:
            api_name: API名称
            
        Returns:
            如果是copy操作则返回True
        """
        return '.copy' in api_name.lower() or 'copy(' in api_name.lower()
    
    def _is_excessive_copy(self, copy_node: PipelineNode, 
                          all_nodes: List[PipelineNode]) -> bool:
        """判断copy操作是否是不必要的
        
        分析后续操作是否真正需要副本，若副本后无修改或原数据未被使用则返回True。
        
        Args:
            copy_node: copy操作节点
            all_nodes: 所有节点列表
            
        Returns:
            如果是不必要的copy操作则返回True
        """
        # 获取副本的输出变量
        copy_output = copy_node.outputs[0] if copy_node.outputs else None
        
        if not copy_output:
            return False
        
        # 查找copy操作之后的所有节点
        subsequent_nodes = [
            node for node in all_nodes
            if node.line_number > copy_node.line_number
        ]
        
        # 分析副本使用情况
        copy_used = False
        original_used = False
        
        for node in subsequent_nodes:
            # 检查是否使用了副本
            if copy_output in node.inputs:
                copy_used = True
                
                # 检查对副本的操作是否是只读操作
                if not self._is_read_only_operation(node.api_name):
                    # 如果是修改操作，则copy可能是必要的
                    return False
            
            # 检查是否使用了原数据
            if any(input_var in node.inputs for input_var in copy_node.inputs):
                original_used = True
        
        # 如果副本未被使用，或者副本只有只读操作且原数据未被使用，则是不必要的
        return not copy_used or (not original_used and 
               all(self._is_read_only_operation(node.api_name) 
                   for node in subsequent_nodes if copy_output in node.inputs))
    
    def _is_read_only_operation(self, api_name: str) -> bool:
        """判断操作是否是只读操作
        
        Args:
            api_name: API名称
            
        Returns:
            如果是只读操作则返回True
        """
        read_only_prefixes = ['info', 'describe', 'head', 'tail', 'shape', 
                             'columns', 'dtypes', 'isna', 'isnull', 'notna', 'notnull',
                             'value_counts', 'nunique', 'unique', 'get']
        
        return any(api_name.startswith(prefix) for prefix in read_only_prefixes)
    
    def _create_excessive_copy_smell(self, copy_node: PipelineNode) -> SmellInstance:
        """创建不必要复制的Smell实例
        
        Args:
            copy_node: copy操作节点
            
        Returns:
            SmellInstance对象
        """
        location = LocationInfo(
            file_path=copy_node.location,
            line_number=copy_node.line_number,
            code_snippet=copy_node.code_snippet
        )
        
        copy_output = copy_node.outputs[0] if copy_node.outputs else '未知变量'
        
        description = (
            f"检测到不必要的数据复制: 对 {copy_output} 执行的.copy()操作可能是多余的。"
            f"后续操作没有修改副本数据，或者可以通过原地操作（inplace=True）避免复制。"
            f"这会增加内存使用，降低性能，可能触发内存不足问题。"
        )
        
        suggestion = (
            f"建议检查 {copy_output} 的后续操作。如果不需要修改数据，可以直接使用原数据。"
            f"如果需要修改，考虑使用inplace=True参数或原地操作方法来避免复制。"
        )
        
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.LOW.value,
            affected_nodes=[copy_node.node_id],
            suggestion=suggestion
        )
    
    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的Pipeline节点列表
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按line_number升序排序的PipelineNode列表
        """
        nodes_data = []
        
        for node_id in pipeline_graph.graph.nodes():
            node_data = pipeline_graph.graph.nodes[node_id]
            
            pipeline_node = PipelineNode(
                node_id=node_id,
                operation_type=node_data.get('operation_type'),
                api_name=node_data.get('api_name', ''),
                inputs=node_data.get('inputs', []),
                outputs=node_data.get('outputs', []),
                line_number=node_data.get('line_number', 0),
                code_snippet=node_data.get('code_snippet', ''),
                location=node_data.get('location', ''),
                attributes=node_data.get('attributes', {})
            )
            nodes_data.append(pipeline_node)
        
        sorted_nodes = sorted(nodes_data, key=lambda x: x.line_number)
        return sorted_nodes


class RedundantOperationDetector(SmellDetector):
    """冗余操作检测器
    
    检测执行操作效果互相抵消或重复的功能，导致操作冗余的情况。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义冲突操作对
        self.conflict_pairs = [
            ('dropna', 'fillna', '删除NaN后填充NaN'),
            ('fillna', 'dropna', '填充NaN后又删除NaN'),
            ('drop', 'fillna', '删除列后填充值'),
            ('drop_duplicates', 'fillna', '去重后填充'),
        ]
        
        # 定义重复删除操作
        self.repeated_operations = [
            'dropna',
            'drop_duplicates',
        ]
        
        self.logger.info("RedundantOperationDetector初始化完成")
    
    def detect(self, pipeline_graph: PipelineGraph, 
               module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的冗余操作
        
        查找冲突的操作序列（如dropna后对同一变量执行fillna），
        根据dataflow建立操作依赖，检测到已完成操作的逆向操作则生成SmellInstance。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序
            
        Returns:
            检测到的Smell实例列表，每个实例代表一处冗余操作问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells
        
        # 构建数据流图，跟踪每个变量的操作历史
        dataflow_history: Dict[str, List[PipelineNode]] = defaultdict(list)
        
        for current_node in nodes:
            # 检查当前节点的输入变量是否与之前的操作冲突
            for input_var in current_node.inputs:
                if input_var in dataflow_history:
                    previous_nodes = dataflow_history[input_var]
                    
                    # 检查是否与之前的操作冲突
                    for prev_node in previous_nodes:
                        conflict_type = self._check_conflict(
                            prev_node.api_name, 
                            current_node.api_name
                        )
                        
                        if conflict_type:
                            smell_instance = self._create_redundant_operation_smell(
                                first_node=prev_node,
                                second_node=current_node,
                                conflict_type=conflict_type,
                                variable=input_var
                            )
                            detected_smells.append(smell_instance)
                            self.logger.warning(
                                f"检测到冗余操作: {prev_node.api_name} 后 {current_node.api_name}, "
                                f"变量: {input_var}"
                            )
            
            # 更新数据流历史
            for output_var in current_node.outputs:
                # 新创建的变量，开始新的历史
                dataflow_history[output_var] = [current_node]
            
            # 输入变量的历史也需要更新（如果操作在原数据上）
            for input_var in current_node.inputs:
                if input_var in dataflow_history:
                    dataflow_history[input_var].append(current_node)
        
        # 额外检查重复的相同操作
        repeated_smells = self._check_repeated_operations(nodes)
        detected_smells.extend(repeated_smells)
        
        self.logger.info(f"RedundantOperation检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells
    
    def _check_conflict(self, first_api: str, second_api: str) -> str:
        """检查两个操作是否冲突
        
        Args:
            first_api: 第一个操作的API名称
            second_api: 第二个操作的API名称
            
        Returns:
            冲突类型描述，如果没有冲突则返回None
        """
        for op1, op2, description in self.conflict_pairs:
            if op1 in first_api.lower() and op2 in second_api.lower():
                return description
        
        return None
    
    def _check_repeated_operations(self, nodes: List[PipelineNode]) -> List[SmellInstance]:
        """检查重复的相同操作
        
        Args:
            nodes: 所有节点列表
            
        Returns:
            检测到的重复操作Smell实例列表
        """
        detected_smells = []
        
        for repeated_op in self.repeated_operations:
            # 找到所有执行该操作的节点
            matching_nodes = [
                node for node in nodes 
                if repeated_op in node.api_name.lower()
            ]
            
            if len(matching_nodes) >= 2:
                # 按行号排序
                sorted_nodes = sorted(matching_nodes, key=lambda x: x.line_number)
                
                # 检查它们是否操作相同的变量
                for i in range(len(sorted_nodes) - 1):
                    first_node = sorted_nodes[i]
                    second_node = sorted_nodes[i + 1]
                    
                    # 检查输入变量是否有重叠
                    common_inputs = set(first_node.inputs) & set(second_node.inputs)
                    
                    if common_inputs:
                        smell_instance = self._create_redundant_operation_smell(
                            first_node=first_node,
                            second_node=second_node,
                            conflict_type=f"重复执行{repeated_op}操作",
                            variable=', '.join(common_inputs)
                        )
                        detected_smells.append(smell_instance)
                        self.logger.warning(
                            f"检测到重复操作: {repeated_op} 对变量 {', '.join(common_inputs)} "
                            f"在第 {first_node.line_number} 行和第 {second_node.line_number} 行重复执行"
                        )
        
        return detected_smells
    
    def _create_redundant_operation_smell(self, first_node: PipelineNode, 
                                          second_node: PipelineNode,
                                          conflict_type: str,
                                          variable: str) -> SmellInstance:
        """创建冗余操作的Smell实例
        
        Args:
            first_node: 第一个操作节点
            second_node: 第二个操作节点
            conflict_type: 冲突类型描述
            variable: 受影响的变量名
            
        Returns:
            SmellInstance对象
        """
        location = LocationInfo(
            file_path=second_node.location,
            line_number=second_node.line_number,
            code_snippet=second_node.code_snippet
        )
        
        description = (
            f"检测到冗余操作: 在第 {first_node.line_number} 行执行 {first_node.api_name} 后，"
            f"在第 {second_node.line_number} 行对变量 '{variable}' 执行 {second_node.api_name}，"
            f"属于 {conflict_type}。这造成计算资源浪费，代码意图不清晰，可能导致错误的数据处理结果。"
        )
        
        suggestion = (
            f"建议检查在第 {first_node.line_number} 行和第 {second_node.line_number} 行之间的逻辑。"
            f"如果是 {conflict_type}，请移除其中一个操作或调整操作顺序。"
        )
        
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.MEDIUM.value,
            affected_nodes=[first_node.node_id, second_node.node_id],
            suggestion=suggestion
        )
    
    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的Pipeline节点列表
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按line_number升序排序的PipelineNode列表
        """
        nodes_data = []
        
        for node_id in pipeline_graph.graph.nodes():
            node_data = pipeline_graph.graph.nodes[node_id]
            
            pipeline_node = PipelineNode(
                node_id=node_id,
                operation_type=node_data.get('operation_type'),
                api_name=node_data.get('api_name', ''),
                inputs=node_data.get('inputs', []),
                outputs=node_data.get('outputs', []),
                line_number=node_data.get('line_number', 0),
                code_snippet=node_data.get('code_snippet', ''),
                location=node_data.get('location', ''),
                attributes=node_data.get('attributes', {})
            )
            nodes_data.append(pipeline_node)
        
        sorted_nodes = sorted(nodes_data, key=lambda x: x.line_number)
        return sorted_nodes
