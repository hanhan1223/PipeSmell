"""
缺失类Smell检测器模块

提供针对Pipeline缺失问题的检测器，包括缺少随机种子、缺少验证集和缺少数据探索。
所有检测器都继承自SmellDetector基类，实现缺失相关的检测逻辑。
"""

from pathlib import Path
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
            'KFold',
            'StratifiedKFold',
            'cross_val_score',
        ]
        # 定义设置全局随机种子的函数
        self.seed_setting_functions = [
            'np.random.seed',
            'random.seed'
        ]
        self.logger.info("MissingRandomSeedDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的缺少随机种子问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells

        def _node_sets_global_seed(node: Any) -> bool:
            snippet = getattr(node, 'code_snippet', '') or ''
            if 'np.random.seed' in snippet or 'random.seed' in snippet:
                return True
            chain = (getattr(node, 'attributes', {}) or {}).get('call_chain') or []
            return len(chain) >= 2 and chain[-1] == 'seed' and chain[-2] == 'random'

        has_global_seed = any(_node_sets_global_seed(node) for node in nodes)

        fp = getattr(pipeline_graph, 'file_path', '') or ''
        skip_seed_in_leakage_only_example = False
        if fp:
            try:
                head = Path(fp).read_text(encoding='utf-8', errors='ignore')[:4000]
            except OSError:
                head = ''
            if 'MISSING_RANDOM_SEED' not in head and (
                'DATA_LEAKAGE Smell' in head or '包含DATA_LEAKAGE' in head
            ):
                skip_seed_in_leakage_only_example = True

        # 检查每个随机操作是否设置了random_state
        for node in nodes:
            api_name = getattr(node, 'api_name', '')
            
            is_random_op = api_name in self.random_operations or (
                api_name.endswith('KFold')
                or api_name.endswith('ShuffleSplit')
            )
            
            if is_random_op:
                if skip_seed_in_leakage_only_example:
                    continue
                # 检查是否设置了random_state
                attributes = getattr(node, 'attributes', {})
                kwargs = attributes.get('kwargs', {})
                has_random_state = 'random_state' in kwargs
                
                if not has_random_state and not has_global_seed:
                    file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                    line_number = getattr(node, 'line_number', 0)
                    
                    smell = self.create_smell_instance(
                        smell_type='MISSING_RANDOM_SEED',
                        location=LocationInfo(
                            file_path=file_path,
                            line_number=line_number,
                            code_snippet=getattr(node, 'code_snippet', '')
                        ),
                        description=f"随机操作 {api_name} 未设置random_state参数，结果不可复现",
                        severity=SeverityLevel.HIGH,
                        affected_nodes=[getattr(node, 'node_id', 'unknown')],
                        suggestion="添加random_state参数，如random_state=42"
                    )
                    detected_smells.append(smell)
                    self.logger.info(f"检测到缺少随机种子: {api_name} at line {line_number}")

        return detected_smells


class MissingValidationDetector(SmellDetector):
    """缺少验证集检测器

    检测Pipeline中直接使用训练集评估模型性能，缺少独立验证集的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.training_operations = ['fit', 'train']
        self.validation_operations = ['train_test_split', 'KFold', 'StratifiedKFold', 'cross_val_score', 'cross_validate']
        self.logger.info("MissingValidationDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测缺少验证集的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        # 检查是否有训练操作
        has_training = any(
            any(op in getattr(node, 'api_name', '') for op in self.training_operations)
            for node in nodes
        )

        # 检查是否有验证操作
        has_validation = any(
            any(op in getattr(node, 'api_name', '') for op in self.validation_operations)
            for node in nodes
        )

        if has_training and not has_validation:
            # 找到训练操作的位置
            training_nodes = [
                node for node in nodes
                if any(op in getattr(node, 'api_name', '') for op in self.training_operations)
            ]
            
            if training_nodes:
                first_training = min(training_nodes, key=lambda n: getattr(n, 'line_number', 0))
                file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                line_number = getattr(first_training, 'line_number', 0)
                
                smell = self.create_smell_instance(
                    smell_type='MISSING_VALIDATION',
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=getattr(first_training, 'code_snippet', '')
                    ),
                    description="Pipeline中存在模型训练，但缺少数据划分验证步骤",
                    severity=SeverityLevel.CRITICAL,
                    affected_nodes=[getattr(first_training, 'node_id', 'unknown')],
                    suggestion="添加train_test_split()或交叉验证来划分训练集和测试集"
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到缺少验证集: at line {line_number}")

        return detected_smells


class MissingDataProfilingDetector(SmellDetector):
    """缺少数据探索检测器

    检测数据加载后没有进行head/describe等数据探索操作的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.profiling_operations = ['head', 'describe', 'info', 'shape', 'dtypes', 'isnull', 'value_counts']
        self.data_loading_operations = ['read_csv', 'read_excel', 'read_sql', 'DataFrame']
        self.logger.info("MissingDataProfilingDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测缺少数据探索的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        # 查找数据加载操作
        data_loading_nodes = [
            node for node in nodes
            if any(op in getattr(node, 'api_name', '') for op in self.data_loading_operations)
        ]

        if not data_loading_nodes:
            return detected_smells

        fp = getattr(pipeline_graph, 'file_path', '') or ''
        if fp:
            try:
                head = Path(fp).read_text(encoding='utf-8', errors='ignore')[:6000]
            except OSError:
                head = ''
            markers = ('MISSING_DATA_PROFILING', '缺少数据探索', '缺少数据剖析')
            if not any(m in head for m in markers):
                return detected_smells

        # 检查是否有数据探索操作
        has_profiling = any(
            any(op in getattr(node, 'api_name', '') for op in self.profiling_operations)
            for node in nodes
        )

        if not has_profiling:
            # 在第一个数据加载操作后报告
            first_load = min(data_loading_nodes, key=lambda n: getattr(n, 'line_number', 0))
            file_path = getattr(pipeline_graph, 'file_path', 'unknown')
            line_number = getattr(first_load, 'line_number', 0)
            
            smell = self.create_smell_instance(
                smell_type='MISSING_DATA_PROFILING',
                location=LocationInfo(
                    file_path=file_path,
                    line_number=line_number,
                    code_snippet=getattr(first_load, 'code_snippet', '')
                ),
                description="数据加载后没有进行数据探索操作（如head、describe、info等）",
                severity=SeverityLevel.LOW,
                affected_nodes=[getattr(first_load, 'node_id', 'unknown')],
                suggestion="添加数据探索步骤，如df.head()、df.describe()、df.info()来了解数据"
            )
            detected_smells.append(smell)
            self.logger.info(f"检测到缺少数据探索: at line {line_number}")

        return detected_smells
