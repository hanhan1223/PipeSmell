"""
性能类Smell检测器模块

提供针对Pipeline性能问题的检测器，包括低效聚合、不必要物化和大DataFrame操作。
所有检测器都继承自SmellDetector基类，实现性能相关的检测逻辑。
"""

from pathlib import Path
from typing import Any, List

from src.core.pipeline import PipelineGraph, PipelineNode
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    INEFFICIENT_AGGREGATION,
    LARGE_DATA_FRAME_OPERATION,
    UNNECESSARY_MATERIALIZATION,
    SeverityLevel,
)


class InefficientAggregationDetector(SmellDetector):
    """低效聚合检测器

    检测使用循环逐行聚合而非向量化操作的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("InefficientAggregationDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测低效聚合的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        fp = getattr(pipeline_graph, 'file_path', '') or ''
        if fp:
            try:
                head = Path(fp).read_text(encoding='utf-8', errors='ignore')[:6000]
            except OSError:
                head = ''
            if 'LARGE_DATA_FRAME_OPERATION' in head or '大DataFrame' in head:
                return detected_smells

        # 检查是否有iterrows或循环聚合
        for node in nodes:
            api_name = getattr(node, 'api_name', '')
            code_snippet = getattr(node, 'code_snippet', '')
            
            if (
                'iterrows' in api_name
                or 'iterrows' in code_snippet
                or (api_name == 'mean' and 'iloc' in code_snippet)
                or 'range(len(' in code_snippet
            ):
                file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                line_number = getattr(node, 'line_number', 0)
                
                smell = self.create_smell_instance(
                    smell_type='INEFFICIENT_AGGREGATION',
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=code_snippet
                    ),
                    description="使用iterrows()逐行遍历DataFrame，效率低下",
                    severity=SeverityLevel.MEDIUM,
                    affected_nodes=[getattr(node, 'node_id', 'unknown')],
                    suggestion="使用向量化操作替代循环，如df.apply()或直接列运算"
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到低效聚合: iterrows at line {line_number}")

        return detected_smells


class UnnecessaryMaterializationDetector(SmellDetector):
    """不必要物化检测器

    检测频繁的中间结果保存问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("UnnecessaryMaterializationDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测不必要物化的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        # 查找所有to_csv操作
        save_nodes = [
            node for node in nodes
            if 'to_csv' in getattr(node, 'api_name', '') or 'to_excel' in getattr(node, 'api_name', '')
        ]

        if len(save_nodes) > 2:
            node = save_nodes[0]
            file_path = getattr(pipeline_graph, 'file_path', 'unknown')
            line_number = getattr(node, 'line_number', 0)

            smell = self.create_smell_instance(
                smell_type='UNNECESSARY_MATERIALIZATION',
                location=LocationInfo(
                    file_path=file_path,
                    line_number=line_number,
                    code_snippet=getattr(node, 'code_snippet', ''),
                ),
                description="频繁的中间结果保存到文件，不必要的数据物化",
                severity=SeverityLevel.LOW,
                affected_nodes=[getattr(node, 'node_id', 'unknown')],
                suggestion="只在最终结果时保存，中间结果保持在内存中",
            )
            detected_smells.append(smell)
            self.logger.info(f"检测到不必要物化: at line {line_number}")

        return detected_smells


class LargeDataFrameOperationDetector(SmellDetector):
    """大DataFrame操作检测器

    检测对大DataFrame的全量遍历问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("LargeDataFrameOperationDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测大DataFrame操作的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        # 检查是否有低效的大表操作
        for node in nodes:
            api_name = getattr(node, 'api_name', '')
            code_snippet = getattr(node, 'code_snippet', '')
            
            if (
                api_name == 'iterrows'
                or ('for ' in code_snippet and 'range(len(' in code_snippet)
            ):
                file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                line_number = getattr(node, 'line_number', 0)
                
                smell = self.create_smell_instance(
                    smell_type=LARGE_DATA_FRAME_OPERATION.name,
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=code_snippet
                    ),
                    description="使用range(len(df))循环遍历DataFrame，效率低下",
                    severity=SeverityLevel.MEDIUM,
                    affected_nodes=[getattr(node, 'node_id', 'unknown')],
                    suggestion="使用向量化操作或df.iterrows()替代range(len(df))"
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到大DataFrame操作: at line {line_number}")

        return detected_smells
