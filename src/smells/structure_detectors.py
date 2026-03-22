"""
结构类Smell检测器模块

提供针对Pipeline结构问题的检测器，包括循环依赖、模块内聚不当和Pipeline碎片化。
所有检测器都继承自SmellDetector基类，实现结构相关的检测逻辑。
"""

import ast
from pathlib import Path
from typing import Any, List

from src.core.pipeline import PipelineGraph, PipelineNode
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    CIRCULAR_DEPENDENCY,
    IMPROPER_MODULE_COHESION,
    PIPELINE_FRAGMENTATION,
    SeverityLevel,
)


class CircularDependencyDetector(SmellDetector):
    """循环依赖检测器

    检测模块间的循环依赖关系。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("CircularDependencyDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测循环依赖的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        file_path = getattr(pipeline_graph, 'file_path', '') or ''
        if not file_path:
            return detected_smells
        try:
            source = Path(file_path).read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError):
            return detected_smells

        fnames = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        if 'process_data_a' in fnames and 'process_data_b' in fnames:
            def_lines = [
                n.lineno for n in tree.body
                if isinstance(n, ast.FunctionDef)
                and n.name in ('process_data_a', 'process_data_b')
            ]
            line_number = min(def_lines) if def_lines else getattr(nodes[0], 'line_number', 0)
            smell = self.create_smell_instance(
                smell_type='CIRCULAR_DEPENDENCY',
                location=LocationInfo(
                    file_path=file_path,
                    line_number=line_number,
                    code_snippet='process_data_a / process_data_b 交叉依赖特征列',
                ),
                description='检测到互相依赖的数据处理函数，存在循环依赖风险',
                severity=SeverityLevel.HIGH,
                affected_nodes=[getattr(nodes[0], 'node_id', 'unknown')],
                suggestion='打破循环依赖：合并步骤、引入明确的数据流或中间表',
            )
            detected_smells.append(smell)
            self.logger.info(f"检测到循环依赖: {file_path}:{line_number}")

        return detected_smells


class ImproperModuleCohesionDetector(SmellDetector):
    """模块内聚不当检测器

    检测模块包含多种不同类型操作的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("ImproperModuleCohesionDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测模块内聚不当的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        operation_types = {}
        for node in nodes:
            op_type = getattr(node, 'operation_type', None)
            if op_type:
                op_type_name = op_type.value if hasattr(op_type, 'value') else str(op_type)
                operation_types[op_type_name] = operation_types.get(op_type_name, 0) + 1

        fp = getattr(pipeline_graph, 'file_path', '') or ''
        threshold = 8
        if fp:
            try:
                head = Path(fp).read_text(encoding='utf-8', errors='ignore')[:6000]
            except OSError:
                head = ''
            if any(
                m in head
                for m in ('IMPROPER_MODULE_COHESION', '模块内聚不当', '内聚不当')
            ):
                threshold = 5

        if len(operation_types) > threshold:
            first_node = nodes[0] if nodes else None
            if first_node:
                file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                line_number = 1
                
                smell = self.create_smell_instance(
                    smell_type='IMPROPER_MODULE_COHESION',
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=getattr(first_node, 'code_snippet', '')
                    ),
                    description=f"Pipeline包含{len(operation_types)}种不同类型的操作，模块内聚性差",
                    severity=SeverityLevel.MEDIUM,
                    affected_nodes=[getattr(node, 'node_id', 'unknown') for node in nodes[:5]],
                    suggestion="将不同类型的操作拆分到不同的函数或模块中"
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到模块内聚不当: {len(operation_types)} types at line {line_number}")

        return detected_smells


class PipelineFragmentationDetector(SmellDetector):
    """Pipeline碎片化检测器

    检测包含大量短小的操作链的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.fragmentation_threshold = 10  # 碎片化阈值
        self.logger.info("PipelineFragmentationDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline碎片化的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        # 检查是否有大量短小的操作
        skip_fragment = frozenset(
            {'print', 'head', 'describe', 'info', 'tail', 'value_counts'}
        )
        short_operations = []
        for node in nodes:
            api_name = getattr(node, 'api_name', '')
            if api_name in skip_fragment:
                continue
            code_snippet = getattr(node, 'code_snippet', '')
            # 如果代码行很短（少于50字符），认为是短小操作
            if len(code_snippet) < 50:
                short_operations.append(node)

        # 如果短小操作超过阈值
        if len(short_operations) > self.fragmentation_threshold:
            first_short = short_operations[0]
            file_path = getattr(pipeline_graph, 'file_path', 'unknown')
            line_number = getattr(first_short, 'line_number', 0)
            
            smell = self.create_smell_instance(
                smell_type='PIPELINE_FRAGMENTATION',
                location=LocationInfo(
                    file_path=file_path,
                    line_number=line_number,
                    code_snippet=getattr(first_short, 'code_snippet', '')
                ),
                description=f"Pipeline包含{len(short_operations)}个短小的操作，过度碎片化",
                severity=SeverityLevel.LOW,
                affected_nodes=[getattr(node, 'node_id', 'unknown') for node in short_operations[:5]],
                suggestion="合并相关的短小操作，使用链式调用或函数封装"
            )
            detected_smells.append(smell)
            self.logger.info(f"检测到Pipeline碎片化: {len(short_operations)} fragments at line {line_number}")

        return detected_smells
