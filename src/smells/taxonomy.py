"""
Pipeline Smell分类体系模块

定义完整的Pipeline Smell类型体系，包括Smell基类、分类枚举、严重性等级和具体的Smell常量对象。
提供Smell的形式化描述和检测模式，用于Pipeline Smell的自动检测和分类。
"""

from dataclasses import dataclass
from enum import Enum
from typing import List

from src.core.logger import Logger


class SmellCategory(Enum):
    """Smell类别枚举
    
    定义Pipeline Smell的六大类别，用于分类和识别不同类型的问题。
    """
    ORDER = "ORDER"  # 顺序相关
    REDUNDANCY = "REDUNDANCY"  # 冗余相关
    MISSING = "MISSING"  # 缺失相关
    PERFORMANCE = "PERFORMANCE"  # 性能相关
    STRUCTURE = "STRUCTURE"  # 结构相关
    REPRODUCIBILITY = "REPRODUCIBILITY"  # 可复现性相关


class SeverityLevel(Enum):
    """Smell严重性等级枚举
    
    定义Smell的严重程度等级，用于优先级排序和问题评估。
    """
    CRITICAL = "CRITICAL"  # 严重
    HIGH = "HIGH"  # 高
    MEDIUM = "MEDIUM"  # 中
    LOW = "LOW"  # 低


@dataclass
class PipelineSmell:
    """Pipeline Smell数据类
    
    表示一个Pipeline Smell实例，包含名称、类别、描述、严重性和检测模式等信息。
    """
    name: str  # Smell名称
    category: SmellCategory  # 类别（SmellCategory枚举值）
    description: str  # 描述
    severity: SeverityLevel  # 严重性（SeverityLevel枚举值）
    detection_pattern: str  # 检测模式


# ========== 顺序类Smells (3种) ==========

DATA_LEAKAGE = PipelineSmell(
    name="DATA_LEAKAGE",
    category=SmellCategory.ORDER,
    description="数据泄露：在训练集和测试集划分之前对整个数据集执行全局统计操作或标准化，导致测试集信息泄露到训练集中。"
                "检测条件：存在StandardScaler.fit()、MinMaxScaler.fit()、RobustScaler.fit()等标准化操作，"
                "且这些操作位于train_test_split()或类似的划分函数之前。"
                "影响：导致模型评估过于乐观，实际部署性能下降。",
    severity=SeverityLevel.CRITICAL,
    detection_pattern="存在StandardScaler.fit()、MinMaxScaler.fit()、RobustScaler.fit()等全局统计操作位于train_test_split()之前"
)

MISSING_EVALUATION = PipelineSmell(
    name="MISSING_EVALUATION",
    category=SmellCategory.ORDER,
    description="缺少模型评估：Pipeline中存在模型训练操作（如fit()），但缺少模型评估操作（如score()、predict()+评估指标计算）。"
                "检测条件：存在fit()或train()等训练操作，但缺少score()、accuracy_score()、f1_score()等评估操作，"
                "且没有模型性能指标的计算。"
                "影响：无法评估模型性能，模型训练结果缺乏依据。",
    severity=SeverityLevel.HIGH,
    detection_pattern="存在fit()或train()训练操作，但缺少score()、accuracy_score()、f1_score()等评估操作"
)

MODULE_ORDER_VIOLATION = PipelineSmell(
    name="MODULE_ORDER_VIOLATION",
    category=SmellCategory.ORDER,
    description="模块顺序违反预期：Pipeline中模块的执行顺序不符合常规的数据处理流程，或依赖关系的模块顺序颠倒。"
                "检测条件：数据清洗操作位于数据加载之前，或模型训练位于特征工程之前，"
                "或验证操作位于训练之前等违反逻辑顺序的情况。"
                "影响：可能导致运行时错误或产生错误的处理结果。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="存在数据清洗在数据加载之前、模型训练在特征工程之前、验证在训练之前等违反逻辑顺序的情况"
)


# ========== 冗余类Smells (3种) ==========

REPEATED_TRANSFORM = PipelineSmell(
    name="REPEATED_TRANSFORM",
    category=SmellCategory.REDUNDANCY,
    description="重复数据转换：对同一数据变量多次执行相同类型的转换操作，造成不必要的重复计算。"
                "检测条件：同一变量连续或相近位置执行两次或多次相同类型的转换（如两次fillna、两次dropna等），"
                "且中间没有其他改变数据状态的操作。"
                "影响：增加计算开销，降低代码可维护性。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="同一变量连续或相近位置执行两次或多次相同类型的转换操作（如重复fillna、dropna等）"
)

EXCESSIVE_COPY = PipelineSmell(
    name="EXCESSIVE_COPY",
    category=SmellCategory.REDUNDANCY,
    description="不必要数据复制：在不必要的情况下对DataFrame进行复制操作，增加内存占用和计算开销。"
                "检测条件：存在.copy()操作，但后续操作不会修改原始数据，或可以通过原地操作（inplace=True）避免复制。"
                "影响：增加内存使用，降低性能，可能触发内存不足问题。",
    severity=SeverityLevel.LOW,
    detection_pattern="存在.copy()操作，但后续操作不会修改原始数据，或可以通过inplace=True避免复制"
)

REDUNDANT_OPERATION = PipelineSmell(
    name="REDUNDANT_OPERATION",
    category=SmellCategory.REDUNDANCY,
    description="冗余操作：执行操作效果互相抵消或重复的功能，导致操作冗余。"
                "检测条件：如dropna()后立即fillna()，或重复删除同一列，或对已经处理过的数据再次执行相同清理操作。"
                "影响：造成计算资源浪费，代码意图不清晰。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="存在操作效果互相抵消或重复的情况（如dropna()后立即fillna()，重复删除同一列等）"
)


# ========== 缺失类Smells (3种) ==========

MISSING_RANDOM_SEED = PipelineSmell(
    name="MISSING_RANDOM_SEED",
    category=SmellCategory.MISSING,
    description="缺少随机种子：涉及随机性的操作未设置random_state参数，导致结果不可复现。"
                "检测条件：train_test_split()、shuffle()、split()、KFold、StratifiedKFold等函数未设置random_state参数，"
                "或在导入库时未设置np.random.seed()或random.seed()。"
                "影响：每次运行结果不一致，影响实验复现和调试。",
    severity=SeverityLevel.HIGH,
    detection_pattern="train_test_split()、shuffle()、split()、KFold、StratifiedKFold等函数未设置random_state参数"
)

MISSING_VALIDATION = PipelineSmell(
    name="MISSING_VALIDATION",
    category=SmellCategory.MISSING,
    description="缺少验证集：Pipeline中直接使用训练集评估模型性能，缺少独立的验证或测试集。"
                "检测条件：存在fit()训练操作，但不存在train_test_split()或交叉验证操作（KFold、cross_val_score等），"
                "且在训练数据上直接调用score()或evaluate()。"
                "影响：无法评估模型泛化能力，存在过拟合风险。",
    severity=SeverityLevel.CRITICAL,
    detection_pattern="存在fit()训练操作，但不存在train_test_split()或交叉验证操作（KFold、cross_val_score等）"
)

MISSING_DATA_PROFILING = PipelineSmell(
    name="MISSING_DATA_PROFILING",
    category=SmellCategory.MISSING,
    description="缺少数据探索：Pipeline直接进行数据处理和建模，缺少初步的数据探索和分析操作。"
                "检测条件：不存在describe()、info()、head()、value_counts()、shape等数据探索操作，"
                "直接进入数据清洗和建模阶段。"
                "影响：可能忽略数据质量问题，导致后续处理不当或模型选择错误。",
    severity=SeverityLevel.LOW,
    detection_pattern="不存在describe()、info()、head()、value_counts()、shape等数据探索操作"
)


# ========== 性能类Smells (3种) ==========

INEFFICIENT_AGGREGATION = PipelineSmell(
    name="INEFFICIENT_AGGREGATION",
    category=SmellCategory.PERFORMANCE,
    description="低效聚合：使用低效的方式进行聚合操作，如多次小聚合而非一次大聚合。"
                "检测条件：对同一数据执行多次groupby().agg()操作而非一次性完成，"
                "或使用迭代而非向量化操作进行聚合。"
                "影响：增加计算时间，降低处理效率。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="对同一数据执行多次groupby().agg()操作而非一次性完成，或使用迭代而非向量化操作"
)

UNNECESSARY_MATERIALIZATION = PipelineSmell(
    name="UNNECESSARY_MATERIALIZATION",
    category=SmellCategory.PERFORMANCE,
    description="不必要中间结果持久化：将中间处理结果不必要地保存到文件或数据库，增加I/O开销。"
                "检测条件：在不需要复用中间结果的情况下执行to_csv()、to_parquet()、to_sql()等持久化操作，"
                "且该结果后续不会被读取使用。"
                "影响：增加磁盘I/O，降低整体执行速度，浪费存储空间。",
    severity=SeverityLevel.LOW,
    detection_pattern="在不需要复用中间结果的情况下执行to_csv()、to_parquet()、to_sql()等持久化操作"
)

LARGE_DATAFRAME_OPERATION = PipelineSmell(
    name="LARGE_DATAFRAME_OPERATION",
    category=SmellCategory.PERFORMANCE,
    description="大DataFrame低效操作：对大型DataFrame执行需要全表扫描或内存复制的高开销操作。"
                "检测条件：对大DataFrame（行数>100万）执行多次copy()、apply()、iterrows()等操作，"
                "或未使用chunking处理大数据文件。"
                "影响：可能导致内存溢出或长时间等待。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="对大DataFrame（行数>100万）执行多次copy()、apply()、iterrows()等高开销操作"
)


# ========== 结构类Smells (3种) ==========

CIRCULAR_DEPENDENCY = PipelineSmell(
    name="CIRCULAR_DEPENDENCY",
    category=SmellCategory.STRUCTURE,
    description="循环依赖：Pipeline操作之间存在循环引用，导致无法形成有效的执行顺序。"
                "检测条件：变量A依赖变量B，变量B又依赖变量A，形成数据依赖环；"
                "或通过数据流分析检测出循环的依赖关系。"
                "影响：导致Pipeline无法执行或产生错误的结果。",
    severity=SeverityLevel.HIGH,
    detection_pattern="存在变量A依赖变量B，变量B又依赖变量A的循环引用关系，或数据流图存在环"
)

IMPROPER_MODULE_COHESION = PipelineSmell(
    name="IMPROPER_MODULE_COHESION",
    category=SmellCategory.STRUCTURE,
    description="模块内聚性差：单个模块执行多个不相关的功能，或功能分散在多个模块中。"
                "检测条件：一个代码单元中混合了数据加载、清洗、建模等不同阶段的功能，"
                "或相关功能分散在多个独立单元中。"
                "影响：降低代码可读性和可维护性，难以复用和测试。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="一个代码单元混合了数据加载、清洗、建模等不同阶段的功能，或相关功能分散过广"
)

PIPELINE_FRAGMENTATION = PipelineSmell(
    name="PIPELINE_FRAGMENTATION",
    category=SmellCategory.STRUCTURE,
    description="Pipeline过于碎片化：将一个简单的数据处理流程拆分成过多的小步骤，增加复杂度。"
                "检测条件：存在大量单步操作（如连续多个单列drop操作），这些操作可以合并为少数几个批量操作。"
                "影响：增加代码行数和复杂度，降低执行效率。",
    severity=SeverityLevel.LOW,
    detection_pattern="存在大量单步操作（如连续多个单列drop操作），可以合并为少数批量操作"
)


# ========== 可复现类Smells (3种) ==========

HARDCODED_PARAMETERS = PipelineSmell(
    name="HARDCODED_PARAMETERS",
    category=SmellCategory.REPRODUCIBILITY,
    description="硬编码参数：关键参数值直接硬编码在代码中，不利于模型调优和实验复现。"
                "检测条件：在函数调用或模型初始化中直接使用硬编码的数值（如random_state=42、max_depth=10），"
                "而非通过配置文件或参数管理。"
                "影响：难以进行参数调优，不同实验配置难以对比。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="在函数调用或模型初始化中直接使用硬编码的数值（如random_state=42、max_depth=10）"
)

LACK_OF_VERSION_CONTROL = PipelineSmell(
    name="LACK_OF_VERSION_CONTROL",
    category=SmellCategory.REPRODUCIBILITY,
    description="缺少版本控制：使用动态数据源或外部依赖而未记录版本，导致结果难以复现。"
                "检测条件：读取数据文件时未指定文件版本号，或使用外部API/数据库而未记录数据快照版本，"
                "或依赖库版本未固定（如未使用requirements.txt或environment.yml）。"
                "影响：数据或依赖变更后无法复现之前的实验结果。",
    severity=SeverityLevel.HIGH,
    detection_pattern="读取数据未指定版本号，使用外部API/数据库未记录快照版本，依赖库版本未固定"
)

NON_DETERMINISTIC_ORDER = PipelineSmell(
    name="NON_DETERMINISTIC_ORDER",
    category=SmellCategory.REPRODUCIBILITY,
    description="非确定性顺序：依赖字典、集合等无序数据结构，或不稳定的排序算法，导致执行顺序不确定。"
                "检测条件：依赖dict.keys()、set()等无序集合的迭代顺序，或使用未指定key的sort()操作，"
                "且顺序对结果有影响。"
                "影响：不同Python版本或环境下可能产生不同结果。",
    severity=SeverityLevel.MEDIUM,
    detection_pattern="依赖dict.keys()、set()等无序集合的迭代顺序，或使用未指定key的sort()操作"
)


def get_all_smells() -> List[PipelineSmell]:
    """获取所有已定义的Smell列表
    
    Returns:
        包含所有18种PipelineSmell对象的列表
    """
    logger = Logger.setup("taxonomy", "logs/taxonomy.log")
    logger.debug("获取所有Pipeline Smell列表")
    
    return [
        # 顺序类
        DATA_LEAKAGE,
        MISSING_EVALUATION,
        MODULE_ORDER_VIOLATION,
        # 冗余类
        REPEATED_TRANSFORM,
        EXCESSIVE_COPY,
        REDUNDANT_OPERATION,
        # 缺失类
        MISSING_RANDOM_SEED,
        MISSING_VALIDATION,
        MISSING_DATA_PROFILING,
        # 性能类
        INEFFICIENT_AGGREGATION,
        UNNECESSARY_MATERIALIZATION,
        LARGE_DATAFRAME_OPERATION,
        # 结构类
        CIRCULAR_DEPENDENCY,
        IMPROPER_MODULE_COHESION,
        PIPELINE_FRAGMENTATION,
        # 可复现类
        HARDCODED_PARAMETERS,
        LACK_OF_VERSION_CONTROL,
        NON_DETERMINISTIC_ORDER
    ]


def get_smells_by_category(category: SmellCategory) -> List[PipelineSmell]:
    """根据类别获取Smell列表
    
    Args:
        category: Smell类别枚举值
        
    Returns:
        指定类别下的所有Smell列表
    """
    logger = Logger.setup("taxonomy", "logs/taxonomy.log")
    logger.debug(f"获取类别 {category.value} 下的Smell列表")
    
    return [smell for smell in get_all_smells() if smell.category == category]


def get_smells_by_severity(severity: SeverityLevel) -> List[PipelineSmell]:
    """根据严重性获取Smell列表
    
    Args:
        severity: 严重性等级枚举值
        
    Returns:
        指定严重性等级下的所有Smell列表
    """
    logger = Logger.setup("taxonomy", "logs/taxonomy.log")
    logger.debug(f"获取严重性 {severity.value} 的Smell列表")
    
    return [smell for smell in get_all_smells() if smell.severity == severity]
