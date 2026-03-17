"""
结构类Smell检测器模块

提供针对Pipeline结构问题的检测器，包括循环依赖、模块内聚性差和Pipeline碎片化。
所有检测器都继承自SmellDetector基类，实现结构相关的检测逻辑。
"""

from typing import List, Set, Dict

from src.core.modules import ModuleBoundaryDetector, ModuleType
from src.core.pipeline import PipelineGraph, PipelineNode
from src.core.logger import Logger
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    CIRCULAR_DEPENDENCY,
    IMPROPER_MODULE_COHESION,
    PIPELINE_FRAGMENTATION,
    SeverityLevel
)


class CircularDependencyDetector(SmellDetector):
    """循环依赖检测器
    
    检测模块间的循环依赖关系，例如模块A依赖模块B，而模块B又依赖模块A。
    循环依赖会导致Pipeline难以理解和维护。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.module_classifier = ModuleBoundaryDetector()
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline中的模块循环依赖
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        
        # 获取模块序列
        module_sequence = pipeline.get_module_sequence()
        if len(module_sequence) < 2:
            return instances
        
        # 构建模块依赖图
        module_graph = self._build_module_graph(pipeline)
        
        # 使用DFS检测循环
        cycles = self._detect_cycles(module_graph)
        
        if cycles:
            # 为每个循环依赖创建Smell实例
            for cycle in cycles:
                cycle_str = " → ".join([module.name for module in cycle])
                
                # 找到涉及循环的具体节点位置
                locations = self._find_cycle_locations(pipeline, cycle)
                
                for location in locations:
                    description = (
                        f"检测到模块循环依赖：{cycle_str}。"
                        f"循环依赖会导致Pipeline难以理解和维护，建议重构模块结构。"
                    )
                    
                    instance = SmellInstance(
                        smell_type=CIRCULAR_DEPENDENCY.name,
                        location=location,
                        description=description,
                        severity=SeverityLevel.CRITICAL,
                        affected_node_ids=[]
                    )
                    
                    instances.append(instance)
        
        return instances
    
    def _build_module_graph(self, pipeline: 'PipelineGraph') -> 'Dict[ModuleType, Set[ModuleType]]':
        """构建模块依赖图
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            模块依赖图 {source_module: {dest_modules}}
        """
        module_graph = {}
        nodes = pipeline.get_nodes()
        
        for node in nodes:
            source_module = node.module_type
            
            if source_module not in module_graph:
                module_graph[source_module] = set()
            
            # 获取该节点的所有后继节点
            successors = pipeline.get_successors(node.id)
            for successor in successors:
                dest_module = successor.module_type
                
                if dest_module != source_module:
                    module_graph[source_module].add(dest_module)
        
        return module_graph
    
    def _detect_cycles(self, graph: 'Dict[ModuleType, Set[ModuleType]]') -> 'List[List[ModuleType]]':
        """检测图中的循环
        
        Args:
            graph: 模块依赖图
            
        Returns:
            检测到的所有循环（每个循环是模块列表）
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: ModuleType):
            """深度优先搜索检测循环"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        # 对所有未访问的节点启动DFS
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def _find_cycle_locations(self, pipeline: 'PipelineGraph', cycle: 'List[ModuleType]') -> 'List[LocationInfo]':
        """找循环涉及的具体代码位置
        
        Args:
            pipeline: Pipeline图对象
            cycle: 循环的模块列表
            
        Returns:
            代码位置列表
        """
        locations = []
        nodes = pipeline.get_nodes()
        
        # 找到循环中第一个模块转换的位置
        cycle_modules = set(cycle)
        for i in range(len(nodes) - 1):
            current_node = nodes[i]
            next_node = nodes[i + 1]
            
            if (current_node.module_type in cycle_modules and 
                next_node.module_type in cycle_modules):
                location = LocationInfo(
                    file_path=pipeline.file_path,
                    line_number=next_node.line_number,
                    column_number=getattr(next_node, 'column_number', -1)
                )
                locations.append(location)
                break  # 只返回一个代表性位置
        
        return locations


class ImproperModuleCohesionDetector(SmellDetector):
    """模块内聚性差检测器
    
    检测模块内部操作的语义一致性，例如一个模块同时包含数据清洗和模型训练操作。
    这违反了单一职责原则，降低代码可维护性。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义每个模块期望包含的操作类型
        self.expected_operations = {
            ModuleType.DATA_ACQUISITION: ['read_csv', 'load', 'open'],
            ModuleType.DATA_CLEANING: ['fillna', 'dropna', 'drop', 'clean'],
            ModuleType.FEATURE_ENGINEERING: ['transform', 'scale', 'encode', 'feature'],
            ModuleType.MODEL_OPERATION: ['fit', 'predict', 'train', 'evaluate'],
            ModuleType.AUXILIARY_LOGIC: ['print', 'log', 'save', 'plot']
        }
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline中的模块内聚性问题
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        nodes = pipeline.get_nodes()
        
        # 按模块分组节点
        module_nodes: Dict[ModuleType, List[PipelineNode]] = {}
        for node in nodes:
            if node.module_type not in module_nodes:
                module_nodes[node.module_type] = []
            module_nodes[node.module_type].append(node)
        
        # 检查每个模块的内聚性
        for module_type, nodes_in_module in module_nodes.items():
            if len(nodes_in_module) < 2:
                continue  # 模块只有一个操作，无法判断内聚性
            
            # 分析模块内的操作多样性
            if self._has_low_cohesion(nodes_in_module):
                # 获取第一个节点的位置作为报告位置
                first_node = nodes_in_module[0]
                location = LocationInfo(
                    file_path=pipeline.file_path,
                    line_number=first_node.line_number,
                    column_number=getattr(first_node, 'column_number', -1)
                )
                
                description = (
                    f"模块 {module_type.name} 的内聚性较差。"
                    f"该模块包含多种不同类型的操作，建议将其拆分为更小的、职责单一的模块。"
                )
                
                instance = SmellInstance(
                    smell_type=IMPROPER_MODULE_COHESION.name,
                    location=location,
                    description=description,
                    severity=SeverityLevel.MEDIUM,
                    affected_node_ids=[node.id for node in nodes_in_module]
                )
                
                instances.append(instance)
        
        return instances
    
    def _has_low_cohesion(self, nodes: List['PipelineNode']) -> bool:
        """判断模块内聚性是否较低
        
        Args:
            nodes: 模块内的节点列表
            
        Returns:
            是否内聚性较低
        """
        if len(nodes) < 2:
            return False
        
        # 提取所有操作的类型
        operations = [node.operation_type.lower() for node in nodes]
        
        # 检查操作的多样性（简化版：检查是否包含多种不同类型的操作）
        unique_operation_types = set()
        for op in operations:
            for exp_module, expected_ops in self.expected_operations.items():
                if any(exp_op in op for exp_op in expected_ops):
                    unique_operation_types.add(exp_module)
        
        # 如果模块包含3种或以上的操作类型，则认为内聚性较差
        return len(unique_operation_types) >= 3


class PipelineFragmentationDetector(SmellDetector):
    """Pipeline碎片化检测器
    
    检测Pipeline是否过度碎片化，即包含大量短小的操作链。
    过度碎片化会增加理解和维护的复杂度。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义"短操作链"的阈值（操作数）
        self.short_chain_threshold = 2
        # 定义"过度碎片化"的阈值（短操作链数量）
        self.fragmentation_threshold = 5
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline是否过度碎片化
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        nodes = pipeline.get_nodes()
        
        if len(nodes) < 3:
            return instances  # Pipeline太短，无法判断碎片化
        
        # 分析Pipeline的分段情况
        segments = self._identify_segments(nodes)
        short_segments = [seg for seg in segments if len(seg) <= self.short_chain_threshold]
        
        # 如果短操作链数量超过阈值，报告为碎片化
        if len(short_segments) >= self.fragmentation_threshold:
            # 获取第一个短操作链的位置
            first_short_segment = short_segments[0]
            first_node = first_short_segment[0]
            
            location = LocationInfo(
                file_path=pipeline.file_path,
                line_number=first_node.line_number,
                column_number=getattr(first_node, 'column_number', -1)
            )
            
            description = (
                f"Pipeline过度碎片化，包含 {len(short_segments)} 个短操作链。"
                f"过度碎片化会增加理解和维护的复杂度，建议考虑合并相关操作。"
            )
            
            instance = SmellInstance(
                smell_type=PIPELINE_FRAGMENTATION.name,
                location=location,
                description=description,
                severity=SeverityLevel.MEDIUM,
                affected_node_ids=[node.id for node in first_short_segment]
            )
            
            instances.append(instance)
        
        return instances
    
    def _identify_segments(self, nodes: List['PipelineNode']) -> List[List['PipelineNode']]:
        """识别Pipeline中的操作分段
        
        Args:
            nodes: Pipeline节点列表
            
        Returns:
            操作分段列表
        """
        segments = []
        current_segment = []
        
        for i, node in enumerate(nodes):
            current_segment.append(node)
            
            # 检查是否到达分段边界
            if i < len(nodes) - 1:
                next_node = nodes[i + 1]
                # 如果两个节点属于不同模块，则认为到达分段边界
                if node.module_type != next_node.module_type:
                    segments.append(current_segment)
                    current_segment = []
            
        # 添加最后一个分段
        if current_segment:
            segments.append(current_segment)
        
        return segments
