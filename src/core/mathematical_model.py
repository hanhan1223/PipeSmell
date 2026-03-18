"""
Pipeline Smell Detection 数学模型实现

提供Pipeline Smell检测的严格数学定义和形式化框架。
基于docs/MATHEMATICAL_MODEL.md中的数学定义。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set, Tuple, Callable, Optional, Any, Union
import networkx as nx
import numpy as np
from scipy import stats

from src.core.logger import Logger


class OperationType(Enum):
    """操作类型枚举 - 对应数学模型中的 op_i"""
    DATA_LOADING = "DATA_LOADING"
    DATA_CLEANING = "DATA_CLEANING"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    MODEL_OPERATION = "MODEL_OPERATION"
    VALIDATION = "VALIDATION"
    TRAIN_TEST_SPLIT = "TRAIN_TEST_SPLIT"
    AUXILIARY = "AUXILIARY"
    OTHER = "OTHER"


class ModuleType(Enum):
    """模块类型枚举 - 对应数学模型中的 M_i"""
    DATA_ACQUISITION = "DATA_ACQUISITION"
    DATA_CLEANING = "DATA_CLEANING"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    MODEL_OPERATION = "MODEL_OPERATION"
    AUXILIARY_LOGIC = "AUXILIARY_LOGIC"


class SmellCategory(Enum):
    """Smell类别枚举"""
    ORDER = "ORDER"
    REDUNDANCY = "REDUNDANCY"
    MISSING = "MISSING"
    PERFORMANCE = "PERFORMANCE"
    STRUCTURE = "STRUCTURE"
    REPRODUCIBILITY = "REPRODUCIBILITY"


class SeverityLevel(Enum):
    """严重性等级枚举"""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


@dataclass
class OperationNode:
    """操作节点 - 对应数学模型中的 v_i = (op_i, I_i, O_i, M_i)"""
    node_id: str
    operation_type: OperationType  # op_i
    inputs: Set[str]  # I_i - 输入变量集合
    outputs: Set[str]  # O_i - 输出变量集合
    module_type: ModuleType  # M_i
    parameters: Dict[str, Any]  # 操作参数
    line_number: int  # 代码行号
    
    def __hash__(self):
        return hash(self.node_id)


@dataclass
class PipelineGraph:
    """Pipeline图 - 对应数学模型中的 P = (V, E)"""
    nodes: Set[OperationNode]  # V - 节点集合
    edges: Set[Tuple[str, str]]  # E - 边集合 (source_id, target_id)
    graph: nx.DiGraph  # NetworkX图表示
    
    def __post_init__(self):
        """构建NetworkX图"""
        self.graph = nx.DiGraph()
        
        # 添加节点
        for node in self.nodes:
            self.graph.add_node(node.node_id, node=node)
        
        # 添加边
        for source_id, target_id in self.edges:
            self.graph.add_edge(source_id, target_id)
    
    def topological_sort(self) -> List[str]:
        """拓扑排序 - 对应数学模型中的 τ(P)"""
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXError:
            # 存在环，返回部分排序
            return list(self.graph.nodes())
    
    def module_sequence(self) -> List[ModuleType]:
        """模块序列 - 对应数学模型中的 S = ⟨m_1, m_2, ..., m_k⟩"""
        topo_order = self.topological_sort()
        sequence = []
        
        for node_id in topo_order:
            node = self.get_node(node_id)
            if node and node.module_type not in sequence:
                sequence.append(node.module_type)
        
        return sequence
    
    def get_node(self, node_id: str) -> Optional[OperationNode]:
        """获取节点"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None
    
    def has_cycle(self) -> bool:
        """检测是否存在环 - 对应数学模型中的循环依赖检测"""
        return not nx.is_directed_acyclic_graph(self.graph)
    
    def get_cycles(self) -> List[List[str]]:
        """获取所有环"""
        try:
            return list(nx.simple_cycles(self.graph))
        except:
            return []


@dataclass
class SmellInstance:
    """Smell实例 - 对应数学模型中的检测结果"""
    smell_type: str
    category: SmellCategory
    severity: SeverityLevel
    affected_nodes: Set[str]
    description: str
    confidence: float  # 检测置信度 [0, 1]
    line_numbers: List[int]
    
    def priority(self, w_severity: float = 0.7, w_confidence: float = 0.3) -> float:
        """计算优先级 - 对应数学模型中的 priority(s)"""
        return w_severity * self.severity.value + w_confidence * self.confidence


class SmellDetector(ABC):
    """Smell检测器抽象基类 - 对应数学模型中的 detector 函数"""
    
    @abstractmethod
    def detect(self, pipeline: PipelineGraph) -> List[SmellInstance]:
        """检测函数 - 对应数学模型中的 detector: P → 2^V"""
        pass
    
    @abstractmethod
    def pattern(self, pipeline: PipelineGraph, node: OperationNode) -> bool:
        """检测模式函数 - 对应数学模型中的 pattern: P → {0, 1}"""
        pass


class MathematicalModel:
    """数学模型主类 - 实现核心数学定义"""
    
    def __init__(self):
        self.logger = Logger.setup('MathematicalModel', 'logs/mathematical_model.log')
    
    # ==================== 基础数学函数 ====================
    
    def data_dependency(self, pipeline: PipelineGraph, v1: str, v2: str) -> bool:
        """数据依赖关系 - 检查 v2 是否依赖于 v1 的输出"""
        node1 = pipeline.get_node(v1)
        node2 = pipeline.get_node(v2)
        
        if not node1 or not node2:
            return False
        
        # 检查 v1 的输出是否是 v2 的输入
        return bool(node1.outputs & node2.inputs)
    
    def execution_order(self, pipeline: PipelineGraph, v1: str, v2: str) -> int:
        """执行顺序 - 返回 v1 相对于 v2 的执行顺序
        
        Returns:
            -1: v1 在 v2 之前
             0: 无法确定顺序
             1: v1 在 v2 之后
        """
        topo_order = pipeline.topological_sort()
        
        try:
            pos1 = topo_order.index(v1)
            pos2 = topo_order.index(v2)
            
            if pos1 < pos2:
                return -1
            elif pos1 > pos2:
                return 1
            else:
                return 0
        except ValueError:
            return 0
    
    def module_transition_valid(self, m1: ModuleType, m2: ModuleType) -> bool:
        """模块转换有效性 - 检查模块序列是否符合预期顺序"""
        # 定义标准的模块执行顺序
        standard_order = [
            ModuleType.DATA_ACQUISITION,
            ModuleType.DATA_CLEANING,
            ModuleType.FEATURE_ENGINEERING,
            ModuleType.MODEL_OPERATION,
            ModuleType.AUXILIARY_LOGIC
        ]
        
        try:
            pos1 = standard_order.index(m1)
            pos2 = standard_order.index(m2)
            return pos1 <= pos2
        except ValueError:
            return True  # 如果模块不在标准顺序中，认为是有效的
    
    # ==================== Smell检测的数学定义 ====================
    
    def detect_data_leakage(self, pipeline: PipelineGraph) -> List[SmellInstance]:
        """数据泄露检测 - 对应数学模型定义2.2"""
        violations = []
        
        # 找到所有标准化操作
        scaling_ops = [
            node for node in pipeline.nodes
            if node.operation_type == OperationType.FEATURE_ENGINEERING
            and any(op in str(node.parameters) for op in ['StandardScaler', 'MinMaxScaler', 'RobustScaler'])
        ]
        
        # 找到所有训练测试划分操作
        split_ops = [
            node for node in pipeline.nodes
            if node.operation_type == OperationType.TRAIN_TEST_SPLIT
        ]
        
        # 检查是否存在标准化在划分之前的情况
        for scaling_node in scaling_ops:
            for split_node in split_ops:
                if self.execution_order(pipeline, scaling_node.node_id, split_node.node_id) == -1:
                    violations.append(SmellInstance(
                        smell_type="DATA_LEAKAGE",
                        category=SmellCategory.ORDER,
                        severity=SeverityLevel.CRITICAL,
                        affected_nodes={scaling_node.node_id, split_node.node_id},
                        description=f"标准化操作 {scaling_node.node_id} 在训练测试划分 {split_node.node_id} 之前执行",
                        confidence=0.95,
                        line_numbers=[scaling_node.line_number, split_node.line_number]
                    ))
        
        return violations
    
    def detect_missing_evaluation(self, pipeline: PipelineGraph) -> List[SmellInstance]:
        """缺少评估检测 - 对应数学模型定义2.3"""
        violations = []
        
        # 找到训练操作
        train_ops = [
            node for node in pipeline.nodes
            if node.operation_type == OperationType.MODEL_OPERATION
            and any(op in str(node.parameters) for op in ['fit', 'train'])
        ]
        
        # 找到评估操作
        eval_ops = [
            node for node in pipeline.nodes
            if node.operation_type == OperationType.MODEL_OPERATION
            and any(op in str(node.parameters) for op in ['score', 'evaluate', 'predict'])
        ]
        
        # 如果有训练但没有评估
        if train_ops and not eval_ops:
            affected_nodes = {node.node_id for node in train_ops}
            violations.append(SmellInstance(
                smell_type="MISSING_EVALUATION",
                category=SmellCategory.ORDER,
                severity=SeverityLevel.HIGH,
                affected_nodes=affected_nodes,
                description="存在模型训练操作但缺少评估操作",
                confidence=0.90,
                line_numbers=[node.line_number for node in train_ops]
            ))
        
        return violations
    
    def detect_repeated_transform(self, pipeline: PipelineGraph) -> List[SmellInstance]:
        """重复转换检测 - 对应数学模型定义2.4"""
        violations = []
        
        # 按变量分组检查转换操作
        var_transforms = {}
        
        for node in pipeline.nodes:
            if node.operation_type in [OperationType.DATA_CLEANING, OperationType.FEATURE_ENGINEERING]:
                for var in node.outputs:
                    if var not in var_transforms:
                        var_transforms[var] = []
                    var_transforms[var].append(node)
        
        # 检查每个变量的转换序列
        for var, transforms in var_transforms.items():
            if len(transforms) > 1:
                # 按执行顺序排序
                transforms.sort(key=lambda n: pipeline.topological_sort().index(n.node_id))
                
                # 检查相邻的转换是否是相同类型
                for i in range(len(transforms) - 1):
                    t1, t2 = transforms[i], transforms[i + 1]
                    
                    if self._same_transform_type(t1, t2):
                        violations.append(SmellInstance(
                            smell_type="REPEATED_TRANSFORM",
                            category=SmellCategory.REDUNDANCY,
                            severity=SeverityLevel.MEDIUM,
                            affected_nodes={t1.node_id, t2.node_id},
                            description=f"变量 {var} 被重复进行相同类型的转换",
                            confidence=0.85,
                            line_numbers=[t1.line_number, t2.line_number]
                        ))
        
        return violations
    
    def detect_circular_dependency(self, pipeline: PipelineGraph) -> List[SmellInstance]:
        """循环依赖检测 - 对应数学模型定义2.8"""
        violations = []
        
        if pipeline.has_cycle():
            cycles = pipeline.get_cycles()
            
            for cycle in cycles:
                violations.append(SmellInstance(
                    smell_type="CIRCULAR_DEPENDENCY",
                    category=SmellCategory.STRUCTURE,
                    severity=SeverityLevel.HIGH,
                    affected_nodes=set(cycle),
                    description=f"检测到循环依赖: {' -> '.join(cycle)}",
                    confidence=1.0,
                    line_numbers=[pipeline.get_node(nid).line_number for nid in cycle if pipeline.get_node(nid)]
                ))
        
        return violations
    
    def detect_pipeline_fragmentation(self, pipeline: PipelineGraph, theta_frag: float = 2.0) -> List[SmellInstance]:
        """Pipeline碎片化检测 - 对应数学模型定义2.9"""
        violations = []
        
        # 计算碎片化指标
        total_nodes = len(pipeline.nodes)
        unique_operations = len(set(node.operation_type for node in pipeline.nodes))
        
        if unique_operations > 0:
            fragmentation_ratio = total_nodes / unique_operations
            
            if fragmentation_ratio > theta_frag:
                violations.append(SmellInstance(
                    smell_type="PIPELINE_FRAGMENTATION",
                    category=SmellCategory.STRUCTURE,
                    severity=SeverityLevel.LOW,
                    affected_nodes=set(node.node_id for node in pipeline.nodes),
                    description=f"Pipeline过于碎片化，碎片化比率: {fragmentation_ratio:.2f}",
                    confidence=0.75,
                    line_numbers=[node.line_number for node in pipeline.nodes]
                ))
        
        return violations
    
    def detect_hardcoded_parameters(self, pipeline: PipelineGraph) -> List[SmellInstance]:
        """硬编码参数检测 - 对应数学模型定义2.10"""
        violations = []
        
        # 定义超参数关键词
        hyperparameter_keys = {
            'n_estimators', 'max_depth', 'learning_rate', 'alpha', 'C',
            'gamma', 'random_state', 'n_components', 'max_iter'
        }
        
        for node in pipeline.nodes:
            if node.operation_type == OperationType.MODEL_OPERATION:
                hardcoded_params = []
                
                for param_name, param_value in node.parameters.items():
                    if (param_name in hyperparameter_keys and 
                        isinstance(param_value, (int, float)) and 
                        param_name != 'random_state'):  # random_state可以硬编码
                        hardcoded_params.append(f"{param_name}={param_value}")
                
                if hardcoded_params:
                    violations.append(SmellInstance(
                        smell_type="HARDCODED_PARAMETERS",
                        category=SmellCategory.REPRODUCIBILITY,
                        severity=SeverityLevel.MEDIUM,
                        affected_nodes={node.node_id},
                        description=f"检测到硬编码超参数: {', '.join(hardcoded_params)}",
                        confidence=0.80,
                        line_numbers=[node.line_number]
                    ))
        
        return violations
    
    # ==================== 评估指标的数学实现 ====================
    
    def precision(self, predicted: Set[str], actual: Set[str]) -> float:
        """精确率 - Precision = |Ŝ ∩ S| / |Ŝ|"""
        if not predicted:
            return 0.0
        return len(predicted & actual) / len(predicted)
    
    def recall(self, predicted: Set[str], actual: Set[str]) -> float:
        """召回率 - Recall = |Ŝ ∩ S| / |S|"""
        if not actual:
            return 0.0
        return len(predicted & actual) / len(actual)
    
    def f1_score(self, predicted: Set[str], actual: Set[str]) -> float:
        """F1分数 - F1 = 2 * P * R / (P + R)"""
        p = self.precision(predicted, actual)
        r = self.recall(predicted, actual)
        
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)
    
    def jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Jaccard相似度 - |A ∩ B| / |A ∪ B|"""
        if not set1 and not set2:
            return 1.0
        
        union = set1 | set2
        if not union:
            return 0.0
        
        intersection = set1 & set2
        return len(intersection) / len(union)
    
    def cohen_d(self, group1: List[float], group2: List[float]) -> float:
        """Cohen's d效应量 - d = (μ₁ - μ₂) / σₚ"""
        if not group1 or not group2:
            return 0.0
        
        mean1, mean2 = np.mean(group1), np.mean(group2)
        std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
        n1, n2 = len(group1), len(group2)
        
        # 合并标准差
        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        return (mean1 - mean2) / pooled_std
    
    def paired_t_test(self, group1: List[float], group2: List[float]) -> Tuple[float, float]:
        """配对t检验 - 返回 (t统计量, p值)"""
        if len(group1) != len(group2) or len(group1) < 2:
            return 0.0, 1.0
        
        return stats.ttest_rel(group1, group2)
    
    # ==================== 辅助函数 ====================
    
    def _same_transform_type(self, node1: OperationNode, node2: OperationNode) -> bool:
        """判断两个节点是否是相同类型的转换"""
        # 简化实现：基于操作类型判断
        return node1.operation_type == node2.operation_type
    
    def complexity_analysis(self, pipeline: PipelineGraph, num_detectors: int) -> Dict[str, str]:
        """复杂度分析 - 对应数学模型定理4.1和4.2"""
        n = len(pipeline.nodes)  # |V|
        m = len(pipeline.edges)  # |E|
        d = num_detectors
        
        time_complexity = f"O({n}² + {m} * {d})"
        space_complexity = f"O({n} + {m})"
        
        return {
            'time_complexity': time_complexity,
            'space_complexity': space_complexity,
            'nodes': str(n),
            'edges': str(m),
            'detectors': str(d)
        }
    
    def validate_pipeline(self, pipeline: PipelineGraph) -> Dict[str, bool]:
        """Pipeline验证 - 检查数学模型的基本假设"""
        return {
            'is_dag': not pipeline.has_cycle(),  # 有向无环图
            'has_nodes': len(pipeline.nodes) > 0,  # 非空节点集
            'connected': nx.is_weakly_connected(pipeline.graph),  # 弱连通
            'valid_edges': all(
                pipeline.get_node(src) and pipeline.get_node(tgt)
                for src, tgt in pipeline.edges
            )  # 边的端点都存在
        }


class SmellDetectionFramework:
    """Smell检测框架 - 对应数学模型算法3.1"""
    
    def __init__(self):
        self.model = MathematicalModel()
        self.detectors: Dict[str, Callable] = {
            'DATA_LEAKAGE': self.model.detect_data_leakage,
            'MISSING_EVALUATION': self.model.detect_missing_evaluation,
            'REPEATED_TRANSFORM': self.model.detect_repeated_transform,
            'CIRCULAR_DEPENDENCY': self.model.detect_circular_dependency,
            'PIPELINE_FRAGMENTATION': self.model.detect_pipeline_fragmentation,
            'HARDCODED_PARAMETERS': self.model.detect_hardcoded_parameters,
        }
        self.logger = Logger.setup('SmellDetectionFramework', 'logs/mathematical_model.log')
    
    def detect_all_smells(self, pipeline: PipelineGraph) -> List[SmellInstance]:
        """检测所有Smell - 对应算法3.1"""
        self.logger.info(f"开始检测Pipeline: {len(pipeline.nodes)} 个节点")
        
        # 1. 验证Pipeline
        validation = self.model.validate_pipeline(pipeline)
        if not validation['is_dag']:
            self.logger.warning("Pipeline包含环，可能影响检测结果")
        
        # 2. 构建拓扑排序
        topo_order = pipeline.topological_sort()
        self.logger.debug(f"拓扑排序: {topo_order}")
        
        # 3. 计算模块序列
        module_seq = pipeline.module_sequence()
        self.logger.debug(f"模块序列: {module_seq}")
        
        # 4. 运行所有检测器
        all_smells = []
        
        for smell_type, detector in self.detectors.items():
            try:
                smells = detector(pipeline)
                all_smells.extend(smells)
                self.logger.debug(f"{smell_type}: 检测到 {len(smells)} 个实例")
            except Exception as e:
                self.logger.error(f"检测器 {smell_type} 执行失败: {e}")
        
        # 5. 按优先级排序
        all_smells.sort(key=lambda s: s.priority(), reverse=True)
        
        self.logger.info(f"检测完成: 共发现 {len(all_smells)} 个Smell")
        
        return all_smells
    
    def analyze_complexity(self, pipeline: PipelineGraph) -> Dict[str, str]:
        """分析检测复杂度"""
        return self.model.complexity_analysis(pipeline, len(self.detectors))
    
    def register_detector(self, smell_type: str, detector: Callable):
        """注册新的检测器"""
        self.detectors[smell_type] = detector
        self.logger.info(f"注册检测器: {smell_type}")
    
    def get_statistics(self, smells: List[SmellInstance]) -> Dict[str, Any]:
        """获取检测统计信息"""
        if not smells:
            return {'total': 0}
        
        by_category = {}
        by_severity = {}
        
        for smell in smells:
            # 按类别统计
            cat = smell.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            
            # 按严重性统计
            sev = smell.severity.name
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return {
            'total': len(smells),
            'by_category': by_category,
            'by_severity': by_severity,
            'avg_confidence': np.mean([s.confidence for s in smells]),
            'avg_priority': np.mean([s.priority() for s in smells])
        }