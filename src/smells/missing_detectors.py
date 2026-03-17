"""
缺失类Smell检测器模块

提供针对Pipeline缺失问题的检测器，包括缺少随机种子、缺少验证集和缺少数据探索。
所有检测器都继承自SmellDetector基类，实现缺失相关的检测逻辑。
"""

from typing import Any, List

from src.core.pipeline import PipelineGraph, PipelineNode
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    MISSING_DATA_PROFILING,
    MISSING_RANDOM_SEED,
    MISSING_VALIDATION,
    SeverityLevel,
)


class MissingRandomSeedDetector(SmellDetector):
    """缺少随机种子检测器

    检测涉及随机性的操作未设置random_state参数，导致结果不可复现的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义需要检查random_state参数的随机操作列表
        self.random_operations = [
            'train_test_split',
            'shuffle',
            'split',
            'KFold',
            'StratifiedKFold',
            'cross_val_score'
        ]
        # 定义设置全局随机种子的函数
        self.seed_setting_functions = [
            'np.random.seed',
            'random.seed'
        ]
        self.logger.info("MissingRandomSeedDetector初始化完成")

    def detect(self, pipeline_graph: PipelineGraph, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的缺少随机种子问题

        遍历Pipeline节点，查找train_test_split、shuffle、split等随机操作，
        检查这些操作的kwargs中是否包含'random_state'参数，
        同时检查是否存在np.random.seed()或random.seed()全局设置。
        若两者都缺失则生成SmellInstance。

        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序

        Returns:
            检测到的Smell实例列表，每个实例代表一处缺少随机种子的问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells

        # 检查是否存在全局随机种子设置
        has_global_seed = any(
            any(seed_func in node.api_name for seed_func in self.seed_setting_functions)
            for node in nodes
        )

        self.logger.debug(f"存在全局随机种子设置: {has_global_seed}")

        # 查找所有随机操作节点
        random_operation_nodes = [
            node for node in nodes
            if self._is_random_operation(node.api_name)
        ]

        self.logger.debug(f"找到 {len(random_operation_nodes)} 个随机操作节点")

        # 检查每个随机操作是否设置了random_state参数
        for node in random_operation_nodes:
            if not has_global_seed:
                has_random_state = self._has_random_state_parameter(node)
                if not has_random_state:
                    smell_instance = self._create_missing_seed_smell(node)
                    detected_smells.append(smell_instance)
                    self.logger.warning(
                        f"检测到缺少随机种子: {node.api_name} 在第 {node.line_number} 行"
                    )

        self.logger.info(f"MissingRandomSeed检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells

    def _is_random_operation(self, api_name: str) -> bool:
        """判断API名称是否为随机操作

        Args:
            api_name: API名称

        Returns:
            如果是随机操作返回True，否则返回False
        """
        return any(op in api_name for op in self.random_operations)

    def _has_random_state_parameter(self, node: PipelineNode) -> bool:
        """检查节点是否设置了random_state参数

        Args:
            node: Pipeline节点

        Returns:
            如果设置了random_state参数返回True，否则返回False
        """
        # 检查attributes中是否包含random_state
        return 'random_state' in node.attributes

    def _create_missing_seed_smell(self, node: PipelineNode) -> SmellInstance:
        """创建缺少随机种子的Smell实例

        Args:
            node: Pipeline节点

        Returns:
            SmellInstance对象
        """
        location = LocationInfo(
            file_path=node.location,
            line_number=node.line_number,
            code_snippet=node.code_snippet
        )
        description = (
            f"随机操作 '{node.api_name}' 未设置random_state参数，"
            "且未设置全局随机种子（np.random.seed或random.seed），"
            "可能导致每次运行结果不一致，影响实验复现。"
        )
        suggestion = (
            f"为 {node.api_name} 添加 random_state 参数，"
            "或在代码开头设置全局随机种子：np.random.seed(42) 或 random.seed(42)"
        )
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.HIGH.value,
            affected_nodes=[node.node_id],
            suggestion=suggestion
        )

    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的节点列表

        Args:
            pipeline_graph: Pipeline图对象

        Returns:
            排序后的节点列表
        """
        try:
            if hasattr(pipeline_graph, 'nodes'):
                nodes_data = pipeline_graph.nodes(data=True)
                node_list = []
                for node_id, node_data in nodes_data:
                    if isinstance(node_data, dict) and 'node' in node_data:
                        node_list.append(node_data['node'])
                    else:
                        self.logger.debug(f"节点 {node_id} 数据格式异常，跳过")
                return sorted(node_list, key=lambda n: n.line_number)
        except Exception as e:
            self.logger.warning(f"获取节点列表失败: {e}")
        return []


class MissingValidationDetector(SmellDetector):
    """缺少验证集检测器

    检测Pipeline中直接使用训练集评估模型性能，缺少独立的验证或测试集。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义验证集划分操作
        self.validation_operations = [
            'train_test_split',
            'KFold',
            'StratifiedKFold',
            'cross_val_score',
            'cross_validate'
        ]
        # 训练操作
        self.training_operations = [
            'fit',
            'train'
        ]
        self.logger.info("MissingValidationDetector初始化完成")

    def detect(self, pipeline_graph: PipelineGraph, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的缺少验证集问题

        检查是否存在train_test_split或KFold等验证集划分操作，
        若Pipeline中只有训练操作无验证则生成SmellInstance。

        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序

        Returns:
            检测到的Smell实例列表，每个实例代表一处缺少验证集的问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells

        # 查找所有验证集划分操作
        validation_nodes = [
            node for node in nodes
            if self._is_validation_operation(node.api_name)
        ]

        # 查找所有训练操作
        training_nodes = [
            node for node in nodes
            if self._is_training_operation(node.api_name)
        ]

        self.logger.debug(f"找到 {len(validation_nodes)} 个验证集划分节点")
        self.logger.debug(f"找到 {len(training_nodes)} 个训练操作节点")

        # 如果存在训练操作但不存在验证集划分操作，则生成SmellInstance
        if training_nodes and not validation_nodes:
            # 使用第一个训练节点生成Smell实例
            for train_node in training_nodes:
                smell_instance = self._create_missing_validation_smell(train_node)
                detected_smells.append(smell_instance)
                self.logger.warning(
                    f"检测到缺少验证集: 训练操作 '{train_node.api_name}' "
                    f"在第 {train_node.line_number} 行，但未发现验证集划分操作"
                )
            # 只报告第一个训练节点以避免重复
            if len(detected_smells) > 1:
                detected_smells = detected_smells[:1]

        self.logger.info(f"MissingValidation检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells

    def _is_validation_operation(self, api_name: str) -> bool:
        """判断API名称是否为验证集划分操作

        Args:
            api_name: API名称

        Returns:
            如果是验证集划分操作返回True，否则返回False
        """
        return any(op in api_name for op in self.validation_operations)

    def _is_training_operation(self, api_name: str) -> bool:
        """判断API名称是否为训练操作

        Args:
            api_name: API名称

        Returns:
            如果是训练操作返回True，否则返回False
        """
        return any(op in api_name for op in self.training_operations)

    def _create_missing_validation_smell(self, node: PipelineNode) -> SmellInstance:
        """创建缺少验证集的Smell实例

        Args:
            node: Pipeline节点

        Returns:
            SmellInstance对象
        """
        location = LocationInfo(
            file_path=node.location,
            line_number=node.line_number,
            code_snippet=node.code_snippet
        )
        description = (
            f"Pipeline中存在训练操作 '{node.api_name}'，但缺少验证集划分步骤 "
            "(如train_test_split、KFold、cross_val_score等)。"
            "直接使用训练集评估模型性能可能导致无法评估模型泛化能力，存在过拟合风险。"
        )
        suggestion = (
            "使用train_test_split划分训练集和测试集，"
            "或使用交叉验证（KFold、StratifiedKFold、cross_val_score等）"
            "来评估模型泛化能力。"
        )
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.CRITICAL.value,
            affected_nodes=[node.node_id],
            suggestion=suggestion
        )

    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的节点列表

        Args:
            pipeline_graph: Pipeline图对象

        Returns:
            排序后的节点列表
        """
        try:
            if hasattr(pipeline_graph, 'nodes'):
                nodes_data = pipeline_graph.nodes(data=True)
                node_list = []
                for node_id, node_data in nodes_data:
                    if isinstance(node_data, dict) and 'node' in node_data:
                        node_list.append(node_data['node'])
                    else:
                        self.logger.debug(f"节点 {node_id} 数据格式异常，跳过")
                return sorted(node_list, key=lambda n: n.line_number)
        except Exception as e:
            self.logger.warning(f"获取节点列表失败: {e}")
        return []


class MissingDataProfilingDetector(SmellDetector):
    """缺少数据探索检测器

    检测Pipeline直接进行数据处理和建模，缺少初步的数据探索和分析操作。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义数据探索操作
        self.profiling_operations = [
            'head',
            'describe',
            'info',
            'shape',
            'value_counts',
            'isnull',
            'isna',
            'duplicated',
            'dtypes',
            'hist',
            'boxplot',
            'scatter'
        ]
        # 定义数据加载操作
        self.data_loading_operations = [
            'read_csv',
            'read_excel',
            'read_json',
            'read_parquet',
            'load',
            'DataFrame'
        ]
        self.logger.info("MissingDataProfilingDetector初始化完成")

    def detect(self, pipeline_graph: PipelineGraph, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的缺少数据探索问题

        检查是否存在数据探索操作（df.head、df.describe、df.info、df.shape等），
        若在数据加载后无任何探索操作则生成SmellInstance。

        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序

        Returns:
            检测到的Smell实例列表，每个实例代表一处缺少数据探索的问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells

        # 找到第一个数据加载操作的行号
        first_load_line = None
        for node in nodes:
            if self._is_data_loading_operation(node.api_name):
                first_load_line = node.line_number
                self.logger.debug(f"找到数据加载操作: {node.api_name} 在第 {node.line_number} 行")
                break

        if first_load_line is None:
            self.logger.debug("未找到数据加载操作，跳过检测")
            return detected_smells

        # 查找数据加载之后的数据探索操作
        profiling_nodes = [
            node for node in nodes
            if node.line_number > first_load_line and self._is_profiling_operation(node.api_name)
        ]

        self.logger.debug(f"在数据加载后找到 {len(profiling_nodes)} 个数据探索节点")

        # 如果数据加载后没有数据探索操作，则生成SmellInstance
        if not profiling_nodes:
            # 找到数据加载节点进行报告
            for node in nodes:
                if self._is_data_loading_operation(node.api_name):
                    smell_instance = self._create_missing_profiling_smell(node)
                    detected_smells.append(smell_instance)
                    self.logger.warning(
                        f"检测到缺少数据探索: 数据加载操作 '{node.api_name}' "
                        f"在第 {node.line_number} 行，但后续未发现数据探索操作"
                    )
                    break

        self.logger.info(f"MissingDataProfiling检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells

    def _is_profiling_operation(self, api_name: str) -> bool:
        """判断API名称是否为数据探索操作

        Args:
            api_name: API名称

        Returns:
            如果是数据探索操作返回True，否则返回False
        """
        return any(op in api_name for op in self.profiling_operations)

    def _is_data_loading_operation(self, api_name: str) -> bool:
        """判断API名称是否为数据加载操作

        Args:
            api_name: API名称

        Returns:
            如果是数据加载操作返回True，否则返回False
        """
        return any(op in api_name for op in self.data_loading_operations)

    def _create_missing_profiling_smell(self, node: PipelineNode) -> SmellInstance:
        """创建缺少数据探索的Smell实例

        Args:
            node: Pipeline节点

        Returns:
            SmellInstance对象
        """
        location = LocationInfo(
            file_path=node.location,
            line_number=node.line_number,
            code_snippet=node.code_snippet
        )
        description = (
            f"在数据加载操作 '{node.api_name}' 之后，缺少数据探索和分析步骤 "
            "(如df.head()、df.describe()、df.info()、df.value_counts()等)。"
            "缺少数据探索可能导致忽略数据质量问题，影响后续处理和模型选择。"
        )
        suggestion = (
            "在数据加载后添加数据探索操作，例如："
            "df.head() 查看前几行数据，"
            "df.describe() 查看统计信息，"
            "df.info() 查看数据类型和缺失值，"
            "df.value_counts() 查看值分布等。"
        )
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.LOW.value,
            affected_nodes=[node.node_id],
            suggestion=suggestion
        )

    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的节点列表

        Args:
            pipeline_graph: Pipeline图对象

        Returns:
            排序后的节点列表
        """
        try:
            if hasattr(pipeline_graph, 'nodes'):
                nodes_data = pipeline_graph.nodes(data=True)
                node_list = []
                for node_id, node_data in nodes_data:
                    if isinstance(node_data, dict) and 'node' in node_data:
                        node_list.append(node_data['node'])
                    else:
                        self.logger.debug(f"节点 {node_id} 数据格式异常，跳过")
                return sorted(node_list, key=lambda n: n.line_number)
        except Exception as e:
            self.logger.warning(f"获取节点列表失败: {e}")
        return []
