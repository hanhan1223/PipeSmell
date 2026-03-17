"""
Pipeline提取器模块

提供Pipeline节点抽象、图构建算法和序列提取功能，用于识别和分析数据管道。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import networkx as nx
from networkx import NetworkXError

from src.core.logger import Logger


class OperationType(Enum):
    """操作类型枚举
    
    定义Pipeline中不同类型的操作，用于分类和识别节点的功能角色。
    """
    DATA_LOADING = "DATA_LOADING"
    DATA_CLEANING = "DATA_CLEANING"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    MODEL_OPERATION = "MODEL_OPERATION"
    VALIDATION = "VALIDATION"
    TRAIN_TEST_SPLIT = "TRAIN_TEST_SPLIT"
    AUXILIARY = "AUXILIARY"
    OTHER = "OTHER"


@dataclass
class PipelineNode:
    """Pipeline节点数据类
    
    表示Pipeline中的一个操作节点，包含操作类型、输入输出变量、代码位置等信息。
    """
    node_id: str
    operation_type: OperationType
    api_name: str
    inputs: List[str]
    outputs: List[str]
    line_number: int
    code_snippet: str
    location: str
    attributes: Dict[str, Any]
    
    @classmethod
    def from_api_call(cls, api_call: Dict[str, Any]) -> 'PipelineNode':
        """根据API调用信息创建PipelineNode
        
        Args:
            api_call: API调用信息字典，包含'name', 'args', 'kwargs', 'return_var', 'line_no'等字段
            
        Returns:
            PipelineNode实例
        """
        api_name = api_call.get('name', '')
        operation_type = cls._match_operation_type(api_name)
        
        return_var = api_call.get('return_var', [])
        outputs = [return_var] if return_var else []
        
        # 提取输入变量（从args和kwargs中提取变量名）
        inputs = []
        for arg in api_call.get('args', []):
            if isinstance(arg, str) and not arg.isdigit():
                inputs.append(arg)
        for value in api_call.get('kwargs', {}).values():
            if isinstance(value, str) and not value.isdigit():
                inputs.append(value)
        
        return cls(
            node_id=f"node_{api_name}_{api_call.get('line_no', 0)}",
            operation_type=operation_type,
            api_name=api_name,
            inputs=inputs,
            outputs=outputs,
            line_number=api_call.get('line_no', 0),
            code_snippet=api_call.get('code_snippet', ''),
            location=api_call.get('location', ''),
            attributes={}
        )
    
    @staticmethod
    def _match_operation_type(api_name: str) -> OperationType:
        """根据API名称匹配操作类型
        
        Args:
            api_name: API名称
            
        Returns:
            匹配的OperationType枚举值
        """
        # 数据加载相关
        data_loading_apis = ['read_csv', 'read_excel', 'read_json', 'read_parquet', 
                            'load', 'from_dict', 'DataFrame']
        if any(api in api_name for api in data_loading_apis):
            return OperationType.DATA_LOADING
        
        # 数据清洗相关
        data_cleaning_apis = ['fillna', 'dropna', 'drop_duplicates', 'drop', 
                             'replace', 'fillna', 'ffill', 'bfill']
        if any(api in api_name for api in data_cleaning_apis):
            return OperationType.DATA_CLEANING
        
        # 特征工程相关
        feature_engineering_apis = ['get_dummies', 'merge', 'groupby', 'apply', 
                                   'StandardScaler', 'MinMaxScaler', 'LabelEncoder',
                                   'OneHotEncoder', 'FeatureUnion', 'ColumnTransformer']
        if any(api in api_name for api in feature_engineering_apis):
            return OperationType.FEATURE_ENGINEERING
        
        # 模型操作相关
        model_operation_apis = ['fit', 'predict', 'score', 'transform', 'fit_transform',
                               'evaluate', 'train']
        if any(api in api_name for api in model_operation_apis):
            return OperationType.MODEL_OPERATION
        
        # 验证相关
        validation_apis = ['cross_val_score', 'validation_curve', 'learning_curve',
                          'cross_validate', 'GridSearchCV', 'RandomizedSearchCV']
        if any(api in api_name for api in validation_apis):
            return OperationType.VALIDATION
        
        # 训练测试分割
        if 'train_test_split' in api_name:
            return OperationType.TRAIN_TEST_SPLIT
        
        # 辅助操作
        auxiliary_apis = ['print', 'logging', 'info', 'debug', 'warn', 'save', 'to_csv']
        if any(api in api_name for api in auxiliary_apis):
            return OperationType.AUXILIARY
        
        return OperationType.OTHER
    
    def to_dict(self) -> Dict[str, Any]:
        """将PipelineNode序列化为字典，兼容JSON序列化
        
        Returns:
            包含节点信息的字典
        """
        return {
            'node_id': self.node_id,
            'operation_type': self.operation_type.value,
            'api_name': self.api_name,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'line_number': self.line_number,
            'code_snippet': self.code_snippet,
            'location': self.location,
            'attributes': self.attributes
        }


class PipelineGraph:
    """Pipeline图构建器
    
    使用有向图表示Pipeline中的节点和数据流关系。
    """
    
    def __init__(self) -> None:
        """初始化Pipeline图"""
        self.graph = nx.DiGraph()
        self._logger = Logger.setup('pipeline_graph', 'logs/pipeline_graph.log')
    
    def add_node(self, node: PipelineNode) -> None:
        """向图中添加节点
        
        Args:
            node: 要添加的PipelineNode实例
        """
        self.graph.add_node(
            node.node_id,
            operation_type=node.operation_type,
            api_name=node.api_name,
            inputs=node.inputs,
            outputs=node.outputs,
            line_number=node.line_number,
            code_snippet=node.code_snippet,
            location=node.location,
            attributes=node.attributes
        )
        self._logger.debug(f"添加节点: {node.node_id}")
    
    def add_edge(self, source_id: str, target_id: str, edge_type: str) -> None:
        """在图中添加有向边
        
        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            edge_type: 边类型，可选值为'data_flow'、'control_flow'或'backward'
            
        Raises:
            ValueError: 当edge_type不是有效值时
        """
        valid_edge_types = {'data_flow', 'control_flow', 'backward'}
        if edge_type not in valid_edge_types:
            raise ValueError(f"edge_type必须是{valid_edge_types}中的一个")
        
        self.graph.add_edge(source_id, target_id, edge_type=edge_type)
        self._logger.debug(f"添加边: {source_id} -> {target_id} ({edge_type})")
    
    def build_from_dependencies(self, nodes: List[PipelineNode], dep_graph: Dict) -> None:
        """根据节点依赖关系构建数据流边
        
        通过分析节点的输入输出变量，在匹配的节点之间添加'data_flow'边。
        
        Args:
            nodes: PipelineNode列表
            dep_graph: 依赖关系图（当前未使用，保留用于未来扩展）
        """
        # 构建输出变量到节点的映射
        output_to_node: Dict[str, str] = {}
        for node in nodes:
            for output_var in node.outputs:
                output_to_node[output_var] = node.node_id
        
        # 为每个节点检查输入，添加数据流边
        for node in nodes:
            for input_var in node.inputs:
                if input_var in output_to_node and output_to_node[input_var] != node.node_id:
                    source_id = output_to_node[input_var]
                    self.add_edge(source_id, node.node_id, 'data_flow')
                    self._logger.debug(f"构建数据流: {source_id} -> {node.node_id} (变量: {input_var})")
    
    def handle_branches_and_loops(self, cf_info: Dict) -> None:
        """处理分支和循环，添加相应的控制流边
        
        Args:
            cf_info: 控制流信息字典，包含循环和条件分支信息
        """
        # 处理循环节点，添加'backward'边
        loops = cf_info.get('loops', [])
        for loop_info in loops:
            loop_nodes = loop_info.get('nodes', [])
            if len(loop_nodes) >= 2:
                # 从最后一个节点到第一个节点添加回退边
                self.add_edge(loop_nodes[-1], loop_nodes[0], 'backward')
                self._logger.debug(f"添加循环边: {loop_nodes[-1]} -> {loop_nodes[0]}")
        
        # 处理条件分支，添加'control_flow'边
        branches = cf_info.get('branches', [])
        for branch_info in branches:
            branch_start = branch_info.get('start_node')
            branch_ends = branch_info.get('end_nodes', [])
            for end_node in branch_ends:
                if branch_start and branch_start != end_node:
                    self.add_edge(branch_start, end_node, 'control_flow')
                    self._logger.debug(f"添加控制流边: {branch_start} -> {end_node}")
    
    def topological_sort(self) -> List[str]:
        """对图进行拓扑排序
        
        Returns:
            拓扑排序后的节点ID列表
            
        Raises:
            ValueError: 当图中存在循环依赖时
        """
        try:
            sorted_nodes = list(nx.topological_sort(self.graph))
            self._logger.debug(f"拓扑排序结果: {sorted_nodes}")
            return sorted_nodes
        except NetworkXError as e:
            self._logger.error(f"拓扑排序失败: 图中存在循环依赖 - {e}")
            raise ValueError("图中存在循环依赖，无法进行拓扑排序") from e
    
    def get_execution_paths(self) -> List[List[str]]:
        """提取所有可能的执行路径
        
        Returns:
            执行路径列表，每条路径是一个节点ID列表
        """
        # 找出所有入度为0的节点（起始节点）和出度为0的节点（结束节点）
        start_nodes = [n for n, d in self.graph.in_degree() if d == 0]
        end_nodes = [n for n, d in self.graph.out_degree() if d == 0]
        
        if not start_nodes:
            self._logger.warning("未找到起始节点（入度为0）")
            return []
        
        if not end_nodes:
            self._logger.warning("未找到结束节点（出度为0）")
            return []
        
        paths = []
        for start in start_nodes:
            for end in end_nodes:
                try:
                    for path in nx.all_simple_paths(self.graph, start, end):
                        paths.append(list(path))
                except nx.NetworkXNoPath:
                    pass
        
        self._logger.debug(f"找到 {len(paths)} 条执行路径")
        return paths
    
    def get_node_by_id(self, node_id: str) -> Optional[PipelineNode]:
        """根据节点ID获取PipelineNode（从图中重建）
        
        Args:
            node_id: 节点ID
            
        Returns:
            PipelineNode实例，如果节点不存在则返回None
        """
        if node_id not in self.graph.nodes:
            return None
        
        node_data = self.graph.nodes[node_id]
        return PipelineNode(
            node_id=node_id,
            operation_type=node_data.get('operation_type', OperationType.OTHER),
            api_name=node_data.get('api_name', ''),
            inputs=node_data.get('inputs', []),
            outputs=node_data.get('outputs', []),
            line_number=node_data.get('line_number', 0),
            code_snippet=node_data.get('code_snippet', ''),
            location=node_data.get('location', ''),
            attributes=node_data.get('attributes', {})
        )


class PipelineSequenceExtractor:
    """Pipeline序列提取器
    
    从Pipeline图中提取和分析不同的执行序列，包括线性序列、分支点、汇合点和主路径等。
    """
    
    def __init__(self, pipeline_graph: PipelineGraph) -> None:
        """初始化序列提取器
        
        Args:
            pipeline_graph: PipelineGraph实例
        """
        self.graph = pipeline_graph
        self._logger = Logger.setup('pipeline_extractor', 'logs/pipeline_extractor.log')
    
    def extract_linear_sequence(self) -> List[PipelineNode]:
        """提取线性执行序列
        
        使用拓扑排序获取节点的执行顺序，并将其映射回PipelineNode对象。
        
        Returns:
            按执行顺序排列的PipelineNode列表
        """
        try:
            sorted_ids = self.graph.topological_sort()
            nodes = []
            for node_id in sorted_ids:
                node = self.graph.get_node_by_id(node_id)
                if node:
                    nodes.append(node)
            
            self._logger.debug(f"提取线性序列，共 {len(nodes)} 个节点")
            return nodes
        except ValueError as e:
            self._logger.error(f"提取线性序列失败: {e}")
            return []
    
    def identify_branch_points(self) -> List[str]:
        """识别分支点（出度大于1的节点）
        
        Returns:
            分支点节点ID列表
        """
        branch_points = [n for n, d in self.graph.graph.out_degree() if d > 1]
        self._logger.debug(f"识别到 {len(branch_points)} 个分支点: {branch_points}")
        return branch_points
    
    def identify_merge_points(self) -> List[str]:
        """识别汇合点（入度大于1的节点）
        
        Returns:
            汇合点节点ID列表
        """
        merge_points = [n for n, d in self.graph.graph.in_degree() if d > 1]
        self._logger.debug(f"识别到 {len(merge_points)} 个汇合点: {merge_points}")
        return merge_points
    
    def extract_main_path(self) -> List[PipelineNode]:
        """提取主路径
        
        基于节点operation_type推断主路径，从DATA_LOADING类型节点开始，
        到MODEL_OPERATION类型节点结束，选择最长的路径。
        
        Returns:
            主路径上的PipelineNode列表
        """
        try:
            # 找到所有起始节点（DATA_LOADING类型，入度为0）
            potential_starts = []
            for node_id in self.graph.graph.nodes:
                node = self.graph.get_node_by_id(node_id)
                if node and node.operation_type == OperationType.DATA_LOADING and self.graph.graph.in_degree(node_id) == 0:
                    potential_starts.append(node_id)
            
            if not potential_starts:
                self._logger.warning("未找到DATA_LOADING类型的起始节点")
                return []
            
            # 找到所有结束节点（MODEL_OPERATION类型，出度为0或接近结束）
            potential_ends = []
            for node_id in self.graph.graph.nodes:
                node = self.graph.get_node_by_id(node_id)
                if node and node.operation_type == OperationType.MODEL_OPERATION:
                    potential_ends.append(node_id)
            
            if not potential_ends:
                self._logger.warning("未找到MODEL_OPERATION类型的结束节点")
                return []
            
            # 获取所有起始到结束的路径，选择最长的一条
            max_path = []
            for start in potential_starts:
                for end in potential_ends:
                    try:
                        for path in nx.all_simple_paths(self.graph.graph, start, end):
                            if len(path) > len(max_path):
                                max_path = path
                    except nx.NetworkXNoPath:
                        pass
            
            if max_path:
                nodes = []
                for node_id in max_path:
                    node = self.graph.get_node_by_id(node_id)
                    if node:
                        nodes.append(node)
                self._logger.debug(f"提取主路径，共 {len(nodes)} 个节点")
                return nodes
            
            self._logger.warning("未找到有效的路径")
            return []
        except Exception as e:
            self._logger.error(f"提取主路径失败: {e}")
            return []
    
    def split_independent_pipelines(self) -> List[List[PipelineNode]]:
        """识别和分割独立的Pipeline子图
        
        使用弱连通分量识别图中独立的部分，每个部分对应一个独立的Pipeline。
        
        Returns:
            独立Pipeline序列列表，每个序列是一个PipelineNode列表
        """
        weak_components = list(nx.weakly_connected_components(self.graph.graph))
        pipelines = []
        
        for component in weak_components:
            nodes = []
            for node_id in component:
                node = self.graph.get_node_by_id(node_id)
                if node:
                    nodes.append(node)
            
            # 按节点ID排序（通常按行号）
            nodes.sort(key=lambda n: n.line_number)
            pipelines.append(nodes)
        
        self._logger.debug(f"识别到 {len(pipelines)} 个独立Pipeline")
        return pipelines
    
    def analyze_pipeline_structure(self) -> Dict[str, Any]:
        """分析Pipeline结构
        
        Returns:
            包含Pipeline结构信息的字典，包括节点数、边数、分支点、汇合点等
        """
        return {
            'total_nodes': self.graph.graph.number_of_nodes(),
            'total_edges': self.graph.graph.number_of_edges(),
            'branch_points': self.identify_branch_points(),
            'merge_points': self.identify_merge_points(),
            'num_branches': len(self.identify_branch_points()),
            'num_merges': len(self.identify_merge_points()),
            'execution_paths': len(self.graph.get_execution_paths()),
            'independent_pipelines': len(self.split_independent_pipelines())
        }
