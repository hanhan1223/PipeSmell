"""
启发式规则检测基线模块

实现基于简单规则的检测方法（Baseline 2）。
使用预定义的if-else规则检测Pipeline Smell。
"""

from typing import Any, Callable, Dict, List

from src.core.logger import Logger
from src.core.modules import ModuleClassifier
from src.core.pipeline import PipelineGraph, PipelineNode
from src.smells.detector import LocationInfo, SmellInstance, DetectionResult
from src.smells.taxonomy import (
    DATA_LEAKAGE,
    EXCESSIVE_COPY,
    HARDCODED_PARAMETERS,
    MISSING_DATA_PROFILING,
    MISSING_RANDOM_SEED,
    MISSING_VALIDATION,
    REDUNDANT_OPERATION,
    SeverityLevel,
)


class HeuristicBaseline:
    """启发式规则检测基线
    
    基于预定义的逻辑规则检测Pipeline Smell。
    这是Baseline 2，使用更复杂的规则而非简单的关键词匹配。
    """
    
    def __init__(self):
        """初始化启发式规则检测基线"""
        self.logger = Logger.setup('HeuristicBaseline', 'logs/baseline.log', 'INFO')
        
        # 定义规则列表
        # 每个规则: {'name': str, 'condition': callable, 'severity': SeverityLevel}
        self.rules = [
            self._create_rule(
                name='MISSING_RANDOM_SEED',
                condition=self._check_missing_random_seed,
                severity=SeverityLevel.HIGH
            ),
            self._create_rule(
                name='MISSING_VALIDATION',
                condition=self._check_missing_validation,
                severity=SeverityLevel.MEDIUM
            ),
            self._create_rule(
                name='DATA_LEAKAGE',
                condition=self._check_data_leakage,
                severity=SeverityLevel.CRITICAL
            ),
            self._create_rule(
                name='REDUNDANT_OPERATION',
                condition=self._check_redundant_operation,
                severity=SeverityLevel.LOW
            ),
            self._create_rule(
                name='EXCESSIVE_COPY',
                condition=self._check_excessive_copy,
                severity=SeverityLevel.LOW
            ),
            self._create_rule(
                name='HARDCODED_PARAMETERS',
                condition=self._check_hardcoded_parameters,
                severity=SeverityLevel.MEDIUM
            ),
            self._create_rule(
                name='MISSING_DATA_PROFILING',
                condition=self._check_missing_data_profiling,
                severity=SeverityLevel.LOW
            ),
        ]
        
        self.logger.info(f"HeuristicBaseline初始化完成，加载了{len(self.rules)}个规则")
    
    def _create_rule(self, name: str, condition: Callable, 
                    severity: SeverityLevel) -> Dict[str, Any]:
        """创建规则字典
        
        Args:
            name: 规则名称
            condition: 条件检查函数
            severity: 严重性级别
            
        Returns:
            规则字典
        """
        return {
            'name': name,
            'condition': condition,
            'severity': severity
        }
    
    def detect(self, pipeline_graph: PipelineGraph, 
              module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的Smell
        
        遍历RULES，对每个规则调用condition函数并传入pipeline和module_sequence参数。
        若condition返回True则生成对应的SmellInstance。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列
            
        Returns:
            检测到的Smell实例列表
        """
        detected_smells = []
        file_path = getattr(pipeline_graph, 'file_path', 'unknown')
        
        # 对每个规则进行检查
        for rule in self.rules:
            rule_name = rule['name']
            condition_func = rule['condition']
            severity = rule['severity']
            
            try:
                # 执行条件检查
                result = condition_func(pipeline_graph, module_sequence)
                
                if isinstance(result, list):
                    # 如果结果是列表，说明检测到多处问题
                    for issue_info in result:
                        smell = self._create_smell_from_issue(
                            rule_name, issue_info, file_path, severity
                        )
                        if smell:
                            detected_smells.append(smell)
                            self.logger.debug(
                                f"规则 {rule_name} 在 {file_path} 检测到问题"
                            )
                elif result:
                    # 如果是单个检测结果
                    smell = self._create_smell_from_result(
                        rule_name, result, file_path, severity
                    )
                    if smell:
                        detected_smells.append(smell)
                        self.logger.debug(
                            f"规则 {rule_name} 在 {file_path} 检测到问题"
                        )
                        
            except Exception as e:
                self.logger.error(f"规则 {rule_name} 执行失败: {e}")
        
        self.logger.info(f"启发式检测完成，找到 {len(detected_smells)} 个Smell")
        return detected_smells
    
    def _check_missing_random_seed(self, pipeline_graph: PipelineGraph, 
                                 module_sequence: List[Any]) -> Any:
        """检查是否缺少随机种子设置
        
        查找train_test_split、shuffle、split等API调用，
        检查其kwargs中是否包含'random_state'参数，
        或检查是否有np.random.seed()、random.seed()全局设置。
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块序列
            
        Returns:
            如果缺少随机种子则返回问题信息，否则返回None
        """
        nodes = pipeline_graph.get_nodes()
        
        # 查找可能需要随机种子的操作
        random_operations = []
        for node in nodes:
            api_name = node.api_name.lower()
            if 'train_test_split' in api_name or 'shuffle' in api_name or 'split' in api_name:
                # 检查代码片段中是否有random_state参数
                has_random_state = 'random_state' in node.code_snippet.lower()
                if not has_random_state:
                    random_operations.append(node)
        
        if random_operations:
            return random_operations  # 返回所有缺少随机种子的节点
        return None
    
    def _check_missing_validation(self, pipeline_graph: PipelineGraph, 
                               module_sequence: List[Any]) -> Any:
        """检查是否缺少验证集
        
        检查是否存在train_test_split或KFold等验证集划分操作，
        若Pipeline中只有训练操作无验证则生成SmellInstance。
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块序列
            
        Returns:
            如果缺少验证则返回问题信息，否则返回None
        """
        nodes = pipeline_graph.get_nodes()
        
        # 查找验证集划分操作
        has_validation_split = any(
            'train_test_split' in node.api_name or 'kf' in node.api_name.lower()
            for node in nodes
        )
        
        # 查找是否有模型训练操作
        has_model_operation = any(
            'fit' in node.api_name and 'train' in node.api_name.lower()
            for node in nodes
        )
        
        if has_model_operation and not has_validation_split:
            return {
                'line_number': len(nodes) // 2,  # 估计位置
                'description': '缺少验证集划分操作，只有训练操作'
            }
        return None
    
    def _check_data_leakage(self, pipeline_graph: PipelineGraph, 
                           module_sequence: List[Any]) -> Any:
        """检查数据泄露问题
        
        查找StandardScaler.fit等操作，
        检查这些操作的line_number是否小于train_test_split的line_number。
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块序列
            
        Returns:
            如果有数据泄露则返回问题信息，否则返回None
        """
        nodes = pipeline_graph.get_nodes()
        
        # 查找fit操作和train_test_split操作
        fit_nodes = [n for n in nodes if '.fit' in n.api_name and 'scaler' in n.api_name.lower()]
        split_nodes = [n for n in nodes if 'train_test_split' in n.api_name]
        
        issues = []
        for fit_node in fit_nodes:
            for split_node in split_nodes:
                if fit_node.line_number < split_node.line_number:
                    issues.append(fit_node)
        
        if issues:
            return issues
        return None
    
    def _check_redundant_operation(self, pipeline_graph: PipelineGraph, 
                                   module_sequence: List[Any]) -> Any:
        """检查冗余操作
        
        查找冲突的操作序列（如dropna后对同一变量执行fillna）。
        根据dataflow建立操作依赖，检测到已完成操作的逆向操作。
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块序列
            
        Returns:
            如果有冗余操作则返回问题信息，否则返回None
        """
        nodes = pipeline_graph.get_nodes()
        
        # 查找连续的冲突操作
        redundant_pairs = []
        for i in range(len(nodes) - 1):
            node1 = nodes[i]
            node2 = nodes[i + 1]
            
            # 检查dropna后fillna
            if 'dropna' in node1.api_name.lower() and 'fillna' in node2.api_name.lower():
                if set(node1.inputs) & set(node2.inputs):
                    redundant_pairs.append((node1, node2))
        
        if redundant_pairs:
            return redundant_pairs
        return None
    
    def _check_excessive_copy(self, pipeline_graph: PipelineGraph, 
                            module_sequence: List[Any]) -> Any:
        """检查不必要的数据复制
        
        检查DataFrame.copy()调用，分析后续操作是否真正需要副本。
        若副本后无修改或原数据未被使用则标记为excessive。
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块序列
            
        Returns:
            如果有过度的复制操作则返回问题信息，否则返回None
        """
        nodes = pipeline_graph.get_nodes()
        
        # 查找所有copy操作
        copy_nodes = [
            (i, node) for i, node in enumerate(nodes)
            if '.copy()' in node.api_name or 'copy' in node.api_name.lower()
        ]
        
        # 检查在短时间内是否有多个copy操作
        excessive_copies = []
        for i, (idx, node) in enumerate(copy_nodes):
            # 检查后面3个节点内是否还有copy操作
            for j in range(i + 1, len(copy_nodes)):
                next_idx, next_node = copy_nodes[j]
                if next_idx - idx <= 3:
                    excessive_copies.append(node)
                else:
                    break
        
        if excessive_copies:
            return excessive_copies
        return None
    
    def _check_hardcoded_parameters(self, pipeline_graph: PipelineGraph, 
                                  module_sequence: List[Any]) -> Any:
        """检查硬编码参数
        
        识别超参数位置的硬编码字面量（如max_depth=5、n_estimators=100）。
        检查AST中的ast.Constant节点出现在API调用keywords中。
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块序列
            
        Returns:
            如果有硬编码参数则返回问题信息，否则返回None
        """
        nodes = pipeline_graph.get_nodes()
        
        # 查找可能的超参数设置
        hardcoded_nodes = []
        for node in nodes:
            code = node.code_snippet
            # 查找常见的超参数名称和整数值
            if any(param in code for param in ['max_depth', 'n_estimators', 'min_samples_split']):
                if '=' in code and any(digit in code for digit in '0123456789'):
                    hardcoded_nodes.append(node)
        
        if hardcoded_nodes:
            return hardcoded_nodes
        return None
    
    def _check_missing_data_profiling(self, pipeline_graph: PipelineGraph, 
                                     module_sequence: List[Any]) -> Any:
        """检查缺少数据探索
        
        检查是否存在数据探索操作（df.head, df.describe, df.info, df.shape等）。
        若在数据加载后无任何探索操作则生成SmellInstance。
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块序列
            
        Returns:
            如果缺少数据探索则返回问题信息，否则返回None
        """
        nodes = pipeline_graph.get_nodes()
        
        # 查找数据探索操作
        profiling_operations = ['head', 'describe', 'info', 'shape', 'columns', 'dtypes']
        has_profiling = any(
            any(op in node.api_name.lower() or op in node.code_snippet.lower()
                for op in profiling_operations)
            for node in nodes
        )
        
        # 查找数据加载操作
        has_data_loading = any('read' in node.api_name.lower() for node in nodes)
        
        if has_data_loading and not has_profiling:
            # 返回数据加载后的节点位置
            data_load_nodes = [n for n in nodes if 'read' in n.api_name.lower()]
            if data_load_nodes:
                return data_load_nodes[0]
        return None
    
    def _create_smell_from_issue(self, rule_name: str, issue_info: Any, 
                                file_path: str, severity: SeverityLevel) -> SmellInstance:
        """从问题信息创建Smell实例
        
        Args:
            rule_name: 规则名称
            issue_info: 问题信息（可能是节点或字典）
            file_path: 文件路径
            severity: 严重性级别
            
        Returns:
            Smell实例，如果无法创建则返回None
        """
        if hasattr(issue_info, 'line_number'):
            # 如果是PipelineNode对象
            location = LocationInfo(
                file_path=file_path,
                line_number=issue_info.line_number,
                column=0,
                code_snippet=issue_info.code_snippet
            )
        elif isinstance(issue_info, dict):
            # 如果是字典
            location = LocationInfo(
                file_path=file_path,
                line_number=issue_info.get('line_number', 0),
                column=0,
                code_snippet=issue_info.get('code_snippet', '')
            )
        else:
            return None
        
        return SmellInstance(
            smell_type=rule_name,
            location=location,
            description=f"通过启发式规则检测到: {rule_name}",
            severity=severity.value,
            affected_nodes=[],
            suggestion=self._get_suggestion(rule_name)
        )
    
    def _create_smell_from_result(self, rule_name: str, result: Any, 
                                  file_path: str, severity: SeverityLevel) -> SmellInstance:
        """从规则结果创建Smell实例（简化版本）
        
        Args:
            rule_name: 规则名称
            result: 规则检查结果
            file_path: 文件路径
            severity: 严重性级别
            
        Returns:
            Smell实例
        """
        if isinstance(result, dict):
            location = LocationInfo(
                file_path=file_path,
                line_number=result.get('line_number', 0),
                column=0,
                code_snippet=result.get('code_snippet', 'N/A')
            )
            description = result.get('description', f"检测到 {rule_name}")
        else:
            location = LocationInfo(
                file_path=file_path,
                line_number=0,
                column=0,
                code_snippet='N/A'
            )
            description = f"检测到 {rule_name}"
        
        return SmellInstance(
            smell_type=rule_name,
            location=location,
            description=description,
            severity=severity.value,
            affected_nodes=[],
            suggestion=self._get_suggestion(rule_name)
        )
    
    def _get_suggestion(self, rule_name: str) -> str:
        """获取规则对应的修复建议
        
        Args:
            rule_name: 规则名称
            
        Returns:
            修复建议字符串
        """
        suggestions = {
            'MISSING_RANDOM_SEED': (
                "在所有随机操作中添加random_state参数以确保结果可复现"
            ),
            'MISSING_VALIDATION': (
                "使用train_test_split或KFold创建验证集，以正确评估模型性能"
            ),
            'DATA_LEAKAGE': (
                "确保数据转换只在训练集上执行，然后应用到测试集"
            ),
            'REDUNDANT_OPERATION': (
                "检查并移除冗余的操作序列，只保留必要的步骤"
            ),
            'EXCESSIVE_COPY': (
                "审查数据复制的必要性，尽量使用引用传递以减少内存使用"
            ),
            'HARDCODED_PARAMETERS': (
                "将超参数提取到配置文件，或使用GridSearchCV进行自动调优"
            ),
            'MISSING_DATA_PROFILING': (
                "在数据加载后添加探索性分析：df.head(), df.describe(), df.info()"
            ),
        }
        return suggestions.get(rule_name, "请review代码并参考最佳实践")
    
    def convert_to_detection_result(self, pipeline_graph: PipelineGraph, 
                                  smells: List[SmellInstance]) -> DetectionResult:
        """将基线结果转换为标准DetectionResult格式
        
        Args:
            pipeline_graph: Pipeline图对象
            smells: Smell实例列表
            
        Returns:
            标准格式的检测结果对象
        """
        import time
        
        pipeline_info = {
            'file_path': getattr(pipeline_graph, 'file_path', 'unknown'),
            'num_nodes': len(pipeline_graph.get_nodes()),
            'num_modules': len(set(node.operation_type for node in pipeline_graph.get_nodes())),
            'num_edges': pipeline_graph.get_num_edges(),
            'method': 'HeuristicBaseline'
        }
        
        result = DetectionResult(
            pipeline_info=pipeline_info,
            detected_smells=smells,
            runtime_ms=0
        )
        
        return result
