"""
Smell检测器模块

提供Smell检测器的基础框架和数据结构，包括Smell实例表示、检测结果和抽象检测器基类。
所有具体的Smell检测器都应继承自SmellDetector基类并实现detect方法。
"""

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
        return self.__class__.__name__.replace('Detector', '').upper()
    
    def create_smell_instance(self, location: LocationInfo, description: str, 
                              severity: str, affected_nodes: List[str], 
                              suggestion: str) -> SmellInstance:
        """创建Smell实例的辅助方法
        
        提供一个便捷方法来创建标准化的SmellInstance对象。
        
        Args:
            location: 位置信息对象
            description: Smell的详细描述
            severity: 严重性级别字符串（如'CRITICAL'、'HIGH'等）
            affected_nodes: 受影响的Pipeline节点ID列表
            suggestion: 修复建议
            
        Returns:
            创建的SmellInstance对象
        """
        return SmellInstance(
            smell_type=self.get_smell_type(),
            location=location,
            description=description,
            severity=severity,
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
                if smell.severity.value == severity]
    
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
            severity = smell.severity.value
            
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
        self._register_default_detectors()
    
    def register(self, detector: SmellDetector) -> None:
        """注册一个检测器
        
        Args:
            detector: 检测器实例
        """
        smell_type = detector.get_smell_type()
        self.detectors[smell_type] = detector
        logger = Logger.setup('DetectorRegistry', 'logs/detector.log', 'INFO')
        logger.info(f"已注册检测器: {smell_type}")
    
    def unregister(self, smell_type: str) -> None:
        """注销一个检测器
        
        Args:
            smell_type: Smell类型名称
        """
        if smell_type in self.detectors:
            del self.detectors[smell_type]
            logger = Logger.setup('DetectorRegistry', 'logs/detector.log', 'INFO')
            logger.info(f"已注销检测器: {smell_type}")
    
    def get_detector(self, smell_type: str) -> SmellDetector:
        """获取指定类型的检测器
        
        Args:
            smell_type: Smell类型名称
            
        Returns:
            检测器实例，如果不存在则返回None
        """
        return self.detectors.get(smell_type)
    
    def get_all_detectors(self) -> List[SmellDetector]:
        """获取所有已注册的检测器
        
        Returns:
            检测器列表
        """
        return list(self.detectors.values())
    
    def detect_single(self, pipeline: 'PipelineGraph',
                     smell_type: str) -> List[SmellInstance]:
        """使用单个检测器检测Pipeline中的Smell
        
        Args:
            pipeline: Pipeline图对象
            smell_type: Smell类型名称
            
        Returns:
            检测到的Smell实例列表
        """
        detector = self.get_detector(smell_type)
        if detector:
            try:
                return detector.detect(pipeline)
            except Exception as e:
                Logger.error(f"检测器 {smell_type} 执行失败: {e}")
                return []
        else:
            logger = Logger.setup('DetectorRegistry', 'logs/detector.log', 'INFO')
            logger.warning(f"未找到检测器: {smell_type}")
            return []
    
    def detect_all(self, pipeline: 'PipelineGraph',
                  categories: List[str] = None) -> DetectionResult:
        """使用所有检测器检测Pipeline中的Smell
        
        Args:
            pipeline: Pipeline图对象
            categories: 可选，指定只检测特定类别的Smell
            
        Returns:
            完整的检测结果对象
        """
        import time
        
        start_time = time.time()
        all_smells = []
        
        # 确定要使用的检测器列表
        if categories:
            detectors = [det for det in self.get_all_detectors()
                        if det.get_smell_type() in categories]
        else:
            detectors = self.get_all_detectors()
        
        logger = Logger.setup('DetectorRegistry', 'logs/detector.log', 'INFO')
        logger.info(f"开始检测Pipeline: {pipeline.file_path}")
        logger.info(f"使用 {len(detectors)} 个检测器")
        
        # 运行所有检测器
        for detector in detectors:
            try:
                smells = detector.detect(pipeline)
                all_smells.extend(smells)
                logger.debug(f"检测器 {detector.get_smell_type()} 找到 {len(smells)} 个Smell")
            except Exception as e:
                logger.error(f"检测器 {detector.get_smell_type()} 执行失败: {e}")
        
        # 去重和排序
        all_smells = self._deduplicate_smells(all_smells)
        all_smells.sort(key=lambda s: s.location.line_number)
        
        runtime = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 构建Pipeline信息
        nodes = pipeline.get_nodes()
        pipeline_info = {
            'file_path': pipeline.file_path,
            'num_nodes': len(nodes),
            'num_modules': len(set(node.operation_type for node in nodes)),
            'num_edges': pipeline.get_num_edges()
        }
        
        result = DetectionResult(
            pipeline_info=pipeline_info,
            detected_smells=all_smells,
            runtime_ms=runtime
        )
        
        logger.info(f"检测完成，共找到 {len(all_smells)} 个Smell，耗时 {runtime:.2f}ms")
        
        return result
    
    def get_supported_smell_types(self) -> List[str]:
        """获取支持的Smell类型列表
        
        Returns:
            Smell类型名称列表
        """
        return list(self.detectors.keys())
    
    def _deduplicate_smells(self, smells: List[SmellInstance]) -> List[SmellInstance]:
        """去重Smell实例
        
        Args:
            smells: Smell实例列表
            
        Returns:
            去重后的Smell实例列表
        """
        seen = set()
        unique_smells = []
        
        for smell in smells:
            # 使用(smell_type, file_path, line_number)作为唯一键
            key = (smell.smell_type,
                   smell.location.file_path,
                   smell.location.line_number)
            
            if key not in seen:
                seen.add(key)
                unique_smells.append(smell)
        
        return unique_smells
    
    def _register_default_detectors(self) -> None:
        """注册默认的检测器"""
        from src.smells.order_detectors import (
            DataLeakageDetector,
            MissingEvaluationDetector,
            ModuleOrderViolationDetector
        )
        from src.smells.redundancy_detectors import (
            RepeatedTransformDetector,
            ExcessiveCopyDetector,
            RedundantOperationDetector
        )
        from src.smells.missing_detectors import (
            MissingRandomSeedDetector,
            MissingValidationDetector,
            MissingDataProfilingDetector
        )
        from src.smells.performance_detectors import (
            InefficientAggregationDetector,
            UnnecessaryMaterializationDetector,
            LargeDataFrameOperationDetector
        )
        from src.smells.structure_detectors import (
            CircularDependencyDetector,
            ImproperModuleCohesionDetector,
            PipelineFragmentationDetector
        )
        from src.smells.reproducibility_detectors import (
            HardcodedParametersDetector,
            LackOfVersionControlDetector,
            NonDeterministicOrderDetector
        )
        
        # 注册所有检测器
        self.register(DataLeakageDetector())
        self.register(MissingEvaluationDetector())
        self.register(ModuleOrderViolationDetector())
        
        self.register(RepeatedTransformDetector())
        self.register(ExcessiveCopyDetector())
        self.register(RedundantOperationDetector())
        
        self.register(MissingRandomSeedDetector())
        self.register(MissingValidationDetector())
        self.register(MissingDataProfilingDetector())
        
        self.register(InefficientAggregationDetector())
        self.register(UnnecessaryMaterializationDetector())
        self.register(LargeDataFrameOperationDetector())
        
        self.register(CircularDependencyDetector())
        self.register(ImproperModuleCohesionDetector())
        self.register(PipelineFragmentationDetector())
        
        self.register(HardcodedParametersDetector())
        self.register(LackOfVersionControlDetector())
        self.register(NonDeterministicOrderDetector())
