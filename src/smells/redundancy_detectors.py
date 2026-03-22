"""
冗余类Smell检测器模块

提供针对Pipeline冗余问题的检测器，包括重复转换、过度复制和冗余操作。
所有检测器都继承自SmellDetector基类，实现冗余相关的检测逻辑。
"""

from typing import Any, List

from src.core.pipeline import PipelineGraph, PipelineNode
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    REPEATED_TRANSFORM,
    EXCESSIVE_COPY,
    REDUNDANT_OPERATION,
    SeverityLevel,
)


class RepeatedTransformDetector(SmellDetector):
    """重复转换检测器

    检测对同一列进行多次相同类型的转换的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.transform_operations = [
            'StandardScaler',
            'MinMaxScaler',
            'RobustScaler',
            'Normalizer',
            'LabelEncoder',
            'OneHotEncoder'
        ]
        self.logger.info("RepeatedTransformDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测重复转换的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        scaler_names = frozenset(
            {'StandardScaler', 'MinMaxScaler', 'RobustScaler', 'Normalizer'}
        )
        scaler_ctors = [n for n in nodes if getattr(n, 'api_name', '') in scaler_names]
        if len(scaler_ctors) >= 2:
            second = scaler_ctors[1]
            file_path = getattr(pipeline_graph, 'file_path', 'unknown')
            line_number = getattr(second, 'line_number', 0)
            detected_smells.append(
                self.create_smell_instance(
                    smell_type='REPEATED_TRANSFORM',
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=getattr(second, 'code_snippet', ''),
                    ),
                    description="对同一数据链使用多种缩放器/重复标准化，操作冗余",
                    severity=SeverityLevel.MEDIUM,
                    affected_nodes=[getattr(second, 'node_id', 'unknown')],
                    suggestion="移除重复的转换操作，只保留一次标准化/归一化",
                )
            )
            self.logger.info(f"检测到重复转换(多缩放器): at line {line_number}")
            return detected_smells

        applied_transforms = []

        for node in nodes:
            api_name = getattr(node, 'api_name', '')

            for transform in self.transform_operations:
                if transform in api_name:
                    for prev_transform in applied_transforms:
                        if prev_transform['type'] == transform:
                            file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                            line_number = getattr(node, 'line_number', 0)

                            smell = self.create_smell_instance(
                                smell_type='REPEATED_TRANSFORM',
                                location=LocationInfo(
                                    file_path=file_path,
                                    line_number=line_number,
                                    code_snippet=getattr(node, 'code_snippet', ''),
                                ),
                                description=f"对同一数据进行多次{transform}转换，操作冗余",
                                severity=SeverityLevel.MEDIUM,
                                affected_nodes=[getattr(node, 'node_id', 'unknown')],
                                suggestion="移除重复的转换操作，只保留一次标准化/归一化",
                            )
                            detected_smells.append(smell)
                            self.logger.info(f"检测到重复转换: {transform} at line {line_number}")
                            break

                    applied_transforms.append({
                        'type': transform,
                        'node': node,
                        'line': getattr(node, 'line_number', 0),
                    })

        return detected_smells


class ExcessiveCopyDetector(SmellDetector):
    """过度复制检测器

    检测不必要的数据复制操作。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("ExcessiveCopyDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测过度复制的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        copy_nodes = [
            node for node in nodes
            if getattr(node, 'api_name', '') == 'copy'
            or '.copy()' in getattr(node, 'api_name', '')
            or 'copy(' in getattr(node, 'api_name', '')
        ]

        # 如果有多于2个copy操作，认为是过度复制
        if len(copy_nodes) > 2:
            for i, node in enumerate(copy_nodes[2:], start=2):  # 从第3个开始报告
                file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                line_number = getattr(node, 'line_number', 0)
                
                smell = self.create_smell_instance(
                    smell_type='EXCESSIVE_COPY',
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=getattr(node, 'code_snippet', '')
                    ),
                    description="不必要的数据复制操作，后续操作不会修改原始数据",
                    severity=SeverityLevel.LOW,
                    affected_nodes=[getattr(node, 'node_id', 'unknown')],
                    suggestion="检查是否真的需要复制，可以使用inplace=True避免复制"
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到过度复制: at line {line_number}")

        return detected_smells


class RedundantOperationDetector(SmellDetector):
    """冗余操作检测器

    检测操作效果互相抵消或重复的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("RedundantOperationDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测冗余操作的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        # 检查dropna后紧跟fillna
        for i in range(len(nodes) - 1):
            current_node = nodes[i]
            next_node = nodes[i + 1]
            
            current_api = getattr(current_node, 'api_name', '')
            next_api = getattr(next_node, 'api_name', '')
            
            # 检查dropna后fillna
            if 'dropna' in current_api and 'fillna' in next_api:
                file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                line_number = getattr(next_node, 'line_number', 0)
                
                smell = self.create_smell_instance(
                    smell_type='REDUNDANT_OPERATION',
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=getattr(next_node, 'code_snippet', '')
                    ),
                    description="dropna()后立即fillna()，操作效果互相抵消",
                    severity=SeverityLevel.MEDIUM,
                    affected_nodes=[
                        getattr(current_node, 'node_id', 'unknown'),
                        getattr(next_node, 'node_id', 'unknown')
                    ],
                    suggestion="根据需求选择只保留dropna或fillna，不要同时使用"
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到冗余操作: dropna+fillna at line {line_number}")

        return detected_smells
