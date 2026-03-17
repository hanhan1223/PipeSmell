"""
模块分类器模块

提供Pipeline操作的模块类型定义、分类算法、边界检测和顺序验证功能，
用于识别和验证数据管道的模块化结构。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from src.core.logger import Logger
from src.core.pipeline import PipelineNode


class ModuleType(Enum):
    """模块类型枚举
    
    定义数据管道中不同功能模块的类型，用于分类和验证模块顺序。
    """
    DATA_ACQUISITION = "DATA_ACQUISITION"  # 数据获取
    DATA_CLEANING = "DATA_CLEANING"  # 数据清洗
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"  # 特征工程
    MODEL_OPERATION = "MODEL_OPERATION"  # 模型操作
    AUXILIARY_LOGIC = "AUXILIARY_LOGIC"  # 辅助逻辑


MODULE_DEFINITIONS: Dict[ModuleType, List[str]] = {
    ModuleType.DATA_ACQUISITION: ['read_csv', 'read_excel', 'load_data'],
    ModuleType.DATA_CLEANING: ['fillna', 'dropna', 'drop_duplicates', 'replace'],
    ModuleType.FEATURE_ENGINEERING: ['get_dummies', 'StandardScaler', 'MinMaxScaler', 'PCA'],
    ModuleType.MODEL_OPERATION: ['train_test_split', 'fit', 'predict', 'score', 'cross_val_score'],
    ModuleType.AUXILIARY_LOGIC: ['print', 'head', 'describe', 'info']
}


MODULE_ORDER_CONSTRAINTS: List[ModuleType] = [
    ModuleType.DATA_ACQUISITION,
    ModuleType.DATA_CLEANING,
    ModuleType.FEATURE_ENGINEERING,
    ModuleType.MODEL_OPERATION
]


@dataclass
class ModuleNode:
    """模块节点数据类
    
    表示带有模块类型标签的Pipeline节点，继承自PipelineNode并新增module_type字段。
    """
    node_id: str
    operation_type: str
    api_name: str
    inputs: List[str]
    outputs: List[str]
    line_number: int
    module_type: ModuleType


@dataclass
class ModuleTransition:
    """模块转换数据类
    
    记录模块类型之间的转换信息，包括源模块、目标模块和转换位置。
    """
    transition_from: ModuleType
    transition_to: ModuleType
    index: int


@dataclass
class OrderViolation:
    """顺序违规数据类
    
    记录模块顺序违规的详细信息，包括违规位置、当前模块和期望模块。
    """
    index: int
    current_module: ModuleType
    expected_module: ModuleType


@dataclass
class ValidationResult:
    """验证结果数据类
    
    包含模块顺序验证的整体结果和具体的违规列表。
    """
    is_valid: bool
    violations: List[OrderViolation]


class ModuleClassifier:
    """模块分类器
    
    根据API操作名称将Pipeline节点分类到不同的模块类型，并生成带有模块标签的节点序列。
    """
    
    def __init__(self, definitions: Dict[ModuleType, List[str]] = None):
        """初始化模块分类器
        
        Args:
            definitions: 模块类型与API名称的映射字典，默认使用MODULE_DEFINITIONS
        """
        self.definitions = definitions if definitions is not None else MODULE_DEFINITIONS
        self.logger = Logger.setup('modules_classifier', 'logs/modules.log')
        self.logger.debug("ModuleClassifier初始化完成")
    
    def classify_node(self, node: PipelineNode) -> ModuleType:
        """对单个Pipeline节点进行模块分类
        
        根据节点的api_name在MODULE_DEFINITIONS中查找对应的模块类型。
        若未匹配到任何模块类型，则返回AUXILIARY_LOGIC。
        
        Args:
            node: 待分类的PipelineNode实例
            
        Returns:
            匹配的ModuleType枚举值
        """
        for module_type, api_list in self.definitions.items():
            if node.api_name in api_list:
                self.logger.debug(f"节点 {node.node_id} 分类为 {module_type.value}")
                return module_type
        
        self.logger.debug(f"节点 {node.node_id} 未匹配，分类为AUXILIARY_LOGIC")
        return ModuleType.AUXILIARY_LOGIC
    
    def classify_pipeline(self, nodes: List[PipelineNode]) -> List[ModuleNode]:
        """对Pipeline节点序列进行批量分类
        
        对每个PipelineNode应用classify_node方法，生成包含module_type信息的ModuleNode列表。
        
        Args:
            nodes: PipelineNode列表
            
        Returns:
            ModuleNode列表，包含原有的PipelineNode信息和新增的module_type字段
        """
        module_nodes = []
        for node in nodes:
            module_type = self.classify_node(node)
            module_node = ModuleNode(
                node_id=node.node_id,
                operation_type=node.operation_type.value,
                api_name=node.api_name,
                inputs=node.inputs,
                outputs=node.outputs,
                line_number=node.line_number,
                module_type=module_type
            )
            module_nodes.append(module_node)
        
        self.logger.info(f"完成 {len(nodes)} 个节点的模块分类")
        return module_nodes
    
    def get_module_sequence(self, module_nodes: List[ModuleNode]) -> List[ModuleType]:
        """从ModuleNode列表中提取模块类型序列
        
        Args:
            module_nodes: ModuleNode列表
            
        Returns:
            ModuleType列表，按节点顺序排列
        """
        return [node.module_type for node in module_nodes]


class ModuleBoundaryDetector:
    """模块边界检测器
    
    识别模块类型之间的转换边界，验证模块顺序是否符合预期约束。
    """
    
    def __init__(self, order_constraints: List[ModuleType] = None):
        """初始化模块边界检测器
        
        Args:
            order_constraints: 模块顺序约束列表，默认使用MODULE_ORDER_CONSTRAINTS
        """
        self.order_constraints = order_constraints if order_constraints is not None else MODULE_ORDER_CONSTRAINTS
        self.logger = Logger.setup('module_boundary_detector', 'logs/modules.log')
        self.logger.debug("ModuleBoundaryDetector初始化完成")
    
    def detect_transitions(self, module_sequence: List[ModuleType]) -> List[ModuleTransition]:
        """检测模块序列中的转换边界
        
        遍历模块序列，识别相邻不同ModuleType的位置，记录转换信息。
        
        Args:
            module_sequence: ModuleType列表
            
        Returns:
            ModuleTransition列表，记录所有模块转换的位置和类型
        """
        transitions = []
        
        for i in range(len(module_sequence) - 1):
            current = module_sequence[i]
            next_module = module_sequence[i + 1]
            
            if current != next_module:
                transition = ModuleTransition(
                    transition_from=current,
                    transition_to=next_module,
                    index=i
                )
                transitions.append(transition)
        
        self.logger.debug(f"检测到 {len(transitions)} 个模块转换边界")
        return transitions
    
    def validate_order(self, module_sequence: List[ModuleType]) -> ValidationResult:
        """验证模块序列是否符合顺序约束
        
        检测是否存在违反MODULE_ORDER_CONSTRAINTS定义的模块转换。
        辅助逻辑模块(AUXILIARY_LOGIC)不参与顺序验证。
        
        Args:
            module_sequence: ModuleType列表
            
        Returns:
            ValidationResult包含验证结果和违规列表
        """
        violations = self.identify_violations(module_sequence)
        is_valid = len(violations) == 0
        
        if is_valid:
            self.logger.info("模块顺序验证通过")
        else:
            self.logger.warning(f"模块顺序验证失败，发现 {len(violations)} 个违规")
        
        return ValidationResult(
            is_valid=is_valid,
            violations=violations
        )
    
    def identify_violations(self, module_sequence: List[ModuleType]) -> List[OrderViolation]:
        """识别所有违反顺序约束的模块转换
        
        检测是否存在"回退"的模块转换（如MODEL_OPERATION后出现DATA_ACQUISITION）。
        跳过辅助逻辑模块(AUXILIARY_LOGIC)的验证。
        
        Args:
            module_sequence: ModuleType列表
            
        Returns:
            OrderViolation列表，包含所有违规的位置和详细信息
        """
        violations = []
        constraint_dict = {module_type: idx for idx, module_type in enumerate(self.order_constraints)}
        
        # 跳过AUXILIARY_LOGIC，找到最后一个已验证的模块类型索引
        last_valid_index = -1
        
        for i, module_type in enumerate(module_sequence):
            if module_type == ModuleType.AUXILIARY_LOGIC:
                continue
            
            if module_type in constraint_dict:
                current_index = constraint_dict[module_type]
                if last_valid_index != -1 and current_index < last_valid_index:
                    # 发现回退转换
                    last_module = module_sequence[i - 1]
                    # 查找期望的下一个有效模块
                    expected_module = None
                    for j in range(i, len(module_sequence)):
                        if module_sequence[j] in constraint_dict and module_sequence[j] != ModuleType.AUXILIARY_LOGIC:
                            expected_module = module_sequence[j]
                            break
                    
                    violation = OrderViolation(
                        index=i,
                        current_module=module_type,
                        expected_module=expected_module if expected_module else module_type
                    )
                    violations.append(violation)
                    self.logger.warning(
                        f"检测到顺序违规: 索引 {i}, 当前 {module_type.value}, "
                        f"前一个 {last_module.value}, 期望 {expected_module.value if expected_module else 'N/A'}"
                    )
                else:
                    last_valid_index = current_index
        
        return violations
