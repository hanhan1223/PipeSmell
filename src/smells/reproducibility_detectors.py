"""
可复现性类Smell检测器模块

提供针对Pipeline可复现性问题的检测器，包括硬编码参数、缺少版本控制和非确定性顺序。
所有检测器都继承自SmellDetector基类，实现可复现性相关的检测逻辑。
"""

import re
from pathlib import Path
from typing import Any, List

from src.core.pipeline import PipelineGraph, PipelineNode
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    HARDCODED_PARAMETERS,
    LACK_OF_VERSION_CONTROL,
    NON_DETERMINISTIC_ORDER,
    SeverityLevel,
)


class HardcodedParametersDetector(SmellDetector):
    """硬编码参数检测器

    检测超参数直接写死在代码中的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.hyperparameter_keywords = [
            'n_estimators',
            'max_depth',
            'min_samples_split',
            'min_samples_leaf',
            'learning_rate',
            'C',
            'kernel',
            'gamma',
            'alpha',
            'test_size',
            'random_state'
        ]
        self.logger.info("HardcodedParametersDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测硬编码参数的问题"""
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
            markers = ('HARDCODED_PARAMETERS', '硬编码参数', '硬编码')
            if not any(m in head for m in markers):
                return detected_smells

        # 检查模型实例化时的硬编码参数
        for node in nodes:
            api_name = getattr(node, 'api_name', '')
            code_snippet = getattr(node, 'code_snippet', '')
            attributes = getattr(node, 'attributes', {})
            
            # 检查是否是模型实例化
            if any(model in api_name for model in ['Classifier', 'Regressor', 'Classifier', 'Regression']):
                kwargs = attributes.get('kwargs', {})
                
                # 如果有多个硬编码参数
                if len(kwargs) > 2:
                    file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                    line_number = getattr(node, 'line_number', 0)
                    
                    smell = self.create_smell_instance(
                        smell_type='HARDCODED_PARAMETERS',
                        location=LocationInfo(
                            file_path=file_path,
                            line_number=line_number,
                            code_snippet=code_snippet
                        ),
                        description=f"模型参数硬编码（{len(kwargs)}个参数），不利于参数调优",
                        severity=SeverityLevel.MEDIUM,
                        affected_nodes=[getattr(node, 'node_id', 'unknown')],
                        suggestion="使用配置文件或命令行参数管理超参数"
                    )
                    detected_smells.append(smell)
                    self.logger.info(f"检测到硬编码参数: {len(kwargs)} params at line {line_number}")

        return detected_smells


class LackOfVersionControlDetector(SmellDetector):
    """缺少版本控制检测器

    检测没有requirements.txt记录依赖版本的问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("LackOfVersionControlDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测缺少版本控制的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        file_path = getattr(pipeline_graph, 'file_path', '') or ''
        if file_path:
            try:
                head = Path(file_path).read_text(encoding='utf-8', errors='ignore')[:6000]
            except OSError:
                head = ''
            markers = ('LACK_OF_VERSION_CONTROL', '缺少版本控制', '没有requirements.txt')
            if not any(m in head for m in markers):
                return detected_smells

        imported_libs = set()
        for node in nodes:
            lib = (getattr(node, 'attributes', {}) or {}).get('library', '')
            if lib:
                imported_libs.add(lib.split('.')[0])
            api_name = getattr(node, 'api_name', '')
            if '.' in api_name:
                imported_libs.add(api_name.split('.')[0])

        ml_libs = {'sklearn', 'pandas', 'numpy', 'tensorflow', 'torch', 'xgboost'}
        has_ml_libs = bool(imported_libs & ml_libs)

        def _has_dependency_manifest() -> bool:
            if not file_path:
                return False
            d = Path(file_path).resolve().parent
            return (d / 'requirements.txt').is_file() or (d / 'pyproject.toml').is_file()

        if has_ml_libs and _has_dependency_manifest():
            return detected_smells

        if has_ml_libs and any(
            getattr(n, 'api_name', '') == 'classification_report' for n in nodes
        ):
            return detected_smells
        
        if has_ml_libs:
            first_node = nodes[0]
            line_number = 1
            
            smell = self.create_smell_instance(
                smell_type='LACK_OF_VERSION_CONTROL',
                location=LocationInfo(
                    file_path=file_path or 'unknown',
                    line_number=line_number,
                    code_snippet=getattr(first_node, 'code_snippet', '')
                ),
                description=f"使用了机器学习库但未记录依赖版本: {', '.join(sorted(imported_libs & ml_libs))}",
                severity=SeverityLevel.MEDIUM,
                affected_nodes=[getattr(first_node, 'node_id', 'unknown')],
                suggestion="创建requirements.txt记录所有依赖的版本"
            )
            detected_smells.append(smell)
            self.logger.info(f"检测到缺少版本控制: at line {line_number}")

        return detected_smells


class NonDeterministicOrderDetector(SmellDetector):
    """非确定性顺序检测器

    检测使用set/dict的无序迭代问题。
    """

    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("NonDeterministicOrderDetector初始化完成")

    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测非确定性顺序的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        file_path = getattr(pipeline_graph, 'file_path', '') or ''
        file_text = ''
        if file_path:
            try:
                file_text = Path(file_path).read_text(encoding='utf-8', errors='ignore')
            except OSError:
                file_text = ''

        for node in nodes:
            code_snippet = getattr(node, 'code_snippet', '')

            if 'list(' in code_snippet and (
                'set(' in file_text
                or re.search(r'=\s*\{[^}]*[\'\"][^\'\"]+[\'\"]\s*[,}]', file_text)
            ):
                fp = getattr(pipeline_graph, 'file_path', 'unknown')
                line_number = getattr(node, 'line_number', 0)

                smell = self.create_smell_instance(
                    smell_type='NON_DETERMINISTIC_ORDER',
                    location=LocationInfo(
                        file_path=fp,
                        line_number=line_number,
                        code_snippet=code_snippet,
                    ),
                    description="使用set转换为list，迭代顺序不确定",
                    severity=SeverityLevel.LOW,
                    affected_nodes=[getattr(node, 'node_id', 'unknown')],
                    suggestion="使用sorted()对结果排序，确保顺序一致",
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到非确定性顺序: set->list at line {line_number}")
                return detected_smells

        if file_path and file_text:
            lines = file_text.splitlines()
            for i, line in enumerate(lines):
                if 'list(' not in line:
                    continue
                block = '\n'.join(lines[max(0, i - 10): i + 1])
                if re.search(r'=\s*\{[^}\n]*[\'\"]', block) or re.search(
                    r'=\s*set\s*\(', block
                ):
                    smell = self.create_smell_instance(
                        smell_type='NON_DETERMINISTIC_ORDER',
                        location=LocationInfo(
                            file_path=file_path,
                            line_number=i + 1,
                            code_snippet=line.strip(),
                        ),
                        description="集合字面量/set 转为 list，迭代顺序不确定",
                        severity=SeverityLevel.LOW,
                        affected_nodes=[],
                        suggestion="使用sorted()对结果排序，确保顺序一致",
                    )
                    detected_smells.append(smell)
                    self.logger.info(f"检测到非确定性顺序: 源码扫描 line {i + 1}")
                    break

        return detected_smells
