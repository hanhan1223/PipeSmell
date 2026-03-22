"""
Smell检测器模块

提供Smell检测器的基础框架和数据结构，包括Smell实例表示、检测结果和抽象检测器基类。
所有具体的Smell检测器都应继承自SmellDetector基类并实现detect方法。
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

from src.core.logger import Logger
from src.smells.taxonomy import SeverityLevel


@dataclass
class LocationInfo:
    """位置信息数据类
    
    记录代码位置的详细信息，包括文件路径、行号、列号和代码片段。
    用于精确定位Smell在源代码中的位置。
    """
    file_path: str  # 文件路径
    line_number: int  # 行号
    column: int = 0  # 列号，默认为0
    code_snippet: str = ""  # 代码片段，默认为空字符串


@dataclass
class SmellInstance:
    """Smell实例数据类
    
    表示检测到的一个具体的Pipeline Smell实例，包含完整的Smell信息。
    """
    smell_type: str  # Smell类型（如DATA_LEAKAGE、REPEATED_TRANSFORM等）
    location: LocationInfo  # 位置信息
    description: str  # 详细描述
    severity: str  # 严重性（取自SeverityLevel枚举值，如'CRITICAL'、'HIGH'等）
    affected_nodes: List[str]  # 影响的Pipeline节点ID列表
    suggestion: str  # 修复建议


class SmellDetector(ABC):
    """Smell检测器抽象基类
    
    所有具体的Smell检测器必须继承此类并实现detect方法。
    提供日志记录、Smell实例创建等通用功能。
    """
    
    def __init__(self):
        """初始化检测器"""
        self.logger = Logger.setup(self.__class__.__name__, 'logs/detector.log', 'INFO')
    
    @abstractmethod
    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的Smell实例
        
        这是一个抽象方法，子类必须实现具体的检测逻辑。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序
            
        Returns:
            检测到的Smell实例列表
            
        Raises:
            NotImplementedError: 子类未实现此方法时抛出
        """
        pass
    
    def get_smell_type(self) -> str:
        """返回检测器对应的Smell类型名称
        
        通过类名推断Smell类型，例如DataLeakageDetector返回'DATA_LEAKAGE'。
        
        Returns:
            Smell类型名称字符串
        """
        class_name = self.__class__.__name__
        # 移除Detector后缀
        if class_name.endswith('Detector'):
            class_name = class_name[:-8]
        # 转换为下划线大写格式
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()
    
    def _get_sorted_nodes(self, pipeline_graph: Any) -> List[Any]:
        """获取按行号排序的节点列表
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按line_number排序的节点列表
        """
        if hasattr(pipeline_graph, 'get_nodes') and callable(pipeline_graph.get_nodes):
            nodes = pipeline_graph.get_nodes()
        elif hasattr(pipeline_graph, 'nodes') and isinstance(
            getattr(pipeline_graph, 'nodes', None), dict
        ):
            nodes = list(pipeline_graph.nodes.values())
        else:
            nodes = []
        return sorted(nodes, key=lambda n: getattr(n, 'line_number', 0))
    
    def create_smell_instance(
        self,
        smell_type: str,
        location: LocationInfo,
        description: str,
        severity: SeverityLevel,
        affected_nodes: List[str],
        suggestion: str
    ) -> SmellInstance:
        """创建Smell实例
        
        Args:
            smell_type: Smell类型名称
            location: 位置信息
            description: 描述
            severity: 严重性级别
            affected_nodes: 影响的节点列表
            suggestion: 修复建议
            
        Returns:
            SmellInstance对象
        """
        return SmellInstance(
            smell_type=smell_type,
            location=location,
            description=description,
            severity=severity.value,
            affected_nodes=affected_nodes,
            suggestion=suggestion
        )


class DetectionResult:
    """检测结果数据类
    
    封装单个Pipeline的完整检测结果，包含Pipeline信息和检测到的所有Smell实例。
    """
    
    def __init__(self, pipeline_info: dict, detected_smells: List[SmellInstance],
                 runtime_ms: float):
        """初始化检测结果
        
        Args:
            pipeline_info: Pipeline信息字典（file_path, num_nodes, etc.）
            detected_smells: 检测到的Smell实例列表
            runtime_ms: 检测运行时间（毫秒）
        """
        self.pipeline_info = pipeline_info
        self.detected_smells = detected_smells
        self.runtime_ms = runtime_ms
    
    def get_smells_by_category(self, category: str) -> List[SmellInstance]:
        """按类别获取Smell实例
        
        Args:
            category: Smell类别名称
            
        Returns:
            该类别的Smell实例列表
        """
        return [smell for smell in self.detected_smells
                if smell.smell_type == category]
    
    def get_smells_by_severity(self, severity: str) -> List[SmellInstance]:
        """按严重性获取Smell实例
        
        Args:
            severity: 严重性级别
            
        Returns:
            该严重性级别的Smell实例列表
        """
        return [smell for smell in self.detected_smells
                if smell.severity == severity]
    
    def get_summary(self) -> dict:
        """获取检测结果摘要
        
        Returns:
            摘要字典（total_smells, by_category, by_severity）
        """
        summary = {
            'total_smells': len(self.detected_smells),
            'by_category': {},
            'by_severity': {}
        }
        
        for smell in self.detected_smells:
            category = smell.smell_type
            severity = smell.severity
            
            summary['by_category'][category] = \
                summary['by_category'].get(category, 0) + 1
            summary['by_severity'][severity] = \
                summary['by_severity'].get(severity, 0) + 1
        
        return summary


class DetectorRegistry:
    """检测器注册表
    
    管理所有Smell检测器实例，提供统一的检测接口和选择性调用功能。
    """
    
    def __init__(self):
        """初始化检测器注册表"""
        self.detectors: Dict[str, SmellDetector] = {}
        self.logger = Logger.setup('DetectorRegistry', 'logs/detector.log', 'INFO')
        self._register_default_detectors()
    
    def register(self, detector: SmellDetector) -> None:
        """注册一个检测器
        
        Args:
            detector: 检测器实例
        """
        smell_type = detector.get_smell_type()
        self.detectors[smell_type] = detector
        self.logger.info(f"已注册检测器: {smell_type}")
    
    def unregister(self, smell_type: str) -> None:
        """注销一个检测器
        
        Args:
            smell_type: Smell类型名称
        """
        if smell_type in self.detectors:
            del self.detectors[smell_type]
            self.logger.info(f"已注销检测器: {smell_type}")
    
    def get_detector(self, smell_type: str) -> SmellDetector:
        """获取指定类型的检测器
        
        Args:
            smell_type: Smell类型名称
            
        Returns:
            检测器实例，如果不存在则返回None
        """
        return self.detectors.get(smell_type)
    
    def list_detectors(self) -> List[str]:
        """列出所有已注册的检测器类型
        
        Returns:
            检测器类型名称列表
        """
        return list(self.detectors.keys())
    
    def detect_all(self, pipeline_graph: Any, module_sequence: List[Any] = None) -> DetectionResult:
        """使用所有检测器检测Pipeline
        
        Args:
            pipeline_graph: Pipeline图对象
            module_sequence: 模块类型序列（可选）
            
        Returns:
            检测结果对象
        """
        import time
        start_time = time.time()
        
        all_smells = []
        get_num_edges = getattr(pipeline_graph, 'get_num_edges', None)
        pipeline_info = {
            'file_path': getattr(pipeline_graph, 'file_path', ''),
            'num_nodes': len(getattr(pipeline_graph, 'nodes', {})),
            'num_edges': get_num_edges() if callable(get_num_edges) else 0,
        }
        
        # 如果没有提供module_sequence，从pipeline_graph提取
        if module_sequence is None:
            module_sequence = self._extract_module_sequence(pipeline_graph)
        
        self.logger.info(f"开始检测Pipeline: {pipeline_info['file_path']}")
        self.logger.info(f"使用 {len(self.detectors)} 个检测器")
        
        for smell_type, detector in self.detectors.items():
            try:
                smells = detector.detect(pipeline_graph, module_sequence)
                all_smells.extend(smells)
            except Exception as e:
                self.logger.error(f"检测器 {smell_type} 执行失败: {e}")
        
        runtime_ms = (time.time() - start_time) * 1000
        self.logger.info(f"检测完成，共找到 {len(all_smells)} 个Smell，耗时 {runtime_ms:.2f}ms")
        
        return DetectionResult(pipeline_info, all_smells, runtime_ms)
    
    def _extract_module_sequence(self, pipeline_graph: Any) -> List[Any]:
        """从Pipeline图提取模块序列
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            模块类型序列
        """
        nodes = self._get_sorted_nodes_from_graph(pipeline_graph)
        module_sequence = []
        for node in nodes:
            if hasattr(node, 'operation_type'):
                module_sequence.append(node.operation_type)
            elif hasattr(node, 'module_type'):
                module_sequence.append(node.module_type)
        return module_sequence
    
    def _get_sorted_nodes_from_graph(self, pipeline_graph: Any) -> List[Any]:
        """从Pipeline图获取排序后的节点
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按行号排序的节点列表
        """
        if hasattr(pipeline_graph, 'get_nodes') and callable(pipeline_graph.get_nodes):
            nodes = pipeline_graph.get_nodes()
        elif hasattr(pipeline_graph, 'nodes') and isinstance(
            getattr(pipeline_graph, 'nodes', None), dict
        ):
            nodes = list(pipeline_graph.nodes.values())
        else:
            nodes = []
        return sorted(nodes, key=lambda n: getattr(n, 'line_number', 0))
    
    def _register_default_detectors(self):
        """注册默认检测器"""
        # 延迟导入避免循环依赖
        try:
            from src.smells.order_detectors import (
                DataLeakageDetector, MissingEvaluationDetector, ModuleOrderViolationDetector
            )
            from src.smells.redundancy_detectors import (
                RepeatedTransformDetector, ExcessiveCopyDetector, RedundantOperationDetector
            )
            from src.smells.missing_detectors import (
                MissingRandomSeedDetector, MissingValidationDetector, MissingDataProfilingDetector
            )
            from src.smells.performance_detectors import (
                InefficientAggregationDetector, UnnecessaryMaterializationDetector, LargeDataFrameOperationDetector
            )
            from src.smells.structure_detectors import (
                CircularDependencyDetector, ImproperModuleCohesionDetector, PipelineFragmentationDetector
            )
            from src.smells.reproducibility_detectors import (
                HardcodedParametersDetector, LackOfVersionControlDetector, NonDeterministicOrderDetector
            )
            
            # 顺序类
            self.register(DataLeakageDetector())
            self.register(MissingEvaluationDetector())
            self.register(ModuleOrderViolationDetector())
            
            # 冗余类
            self.register(RepeatedTransformDetector())
            self.register(ExcessiveCopyDetector())
            self.register(RedundantOperationDetector())
            
            # 缺失类
            self.register(MissingRandomSeedDetector())
            self.register(MissingValidationDetector())
            self.register(MissingDataProfilingDetector())
            
            # 性能类
            self.register(InefficientAggregationDetector())
            self.register(UnnecessaryMaterializationDetector())
            self.register(LargeDataFrameOperationDetector())
            
            # 结构类
            self.register(CircularDependencyDetector())
            self.register(ImproperModuleCohesionDetector())
            self.register(PipelineFragmentationDetector())
            
            # 可复现性类
            self.register(HardcodedParametersDetector())
            self.register(LackOfVersionControlDetector())
            self.register(NonDeterministicOrderDetector())
            
        except Exception as e:
            self.logger.error(f"注册默认检测器失败: {e}")
