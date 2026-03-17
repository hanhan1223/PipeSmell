"""
性能类Smell检测器模块

提供针对Pipeline性能问题的检测器，包括低效聚合、不必要的中间结果持久化和大数据集低效操作。
所有检测器都继承自SmellDetector基类，实现性能相关的检测逻辑。
"""

from typing import List, Set

from src.core.pipeline import PipelineGraph, PipelineNode
from src.core.logger import Logger
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    INEFFICIENT_AGGREGATION,
    UNNECESSARY_MATERIALIZATION,
    LARGE_DATAFRAME_OPERATION,
    SeverityLevel
)


class InefficientAggregationDetector(SmellDetector):
    """低效聚合检测器
    
    检测使用循环进行逐行聚合而非向量化操作的性能问题。
    例如：使用for循环迭代DataFrame逐行进行累加，而非使用df.groupby().sum()。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义应该避免的逐行操作模式
        self.inefficient_patterns = [
            'for.*in.*iterrows',
            'for.*in.*itertuples',
            'for.*index.*range.*len.*df',
        ]
        # 定义推荐的向量化替代操作
        self.recommended_operations = [
            'groupby',
            'applymap',
            'transform',
            'agg',
            'aggregate',
            'sum',
            'mean',
            'std'
        ]
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline中的低效聚合操作
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        nodes = pipeline.get_nodes()
        
        for node in nodes:
            code_snippet = node.code_snippet.lower()
            
            # 检查是否存在低效的逐行聚合模式
            for pattern in self.inefficient_patterns:
                if self._match_pattern(code_snippet, pattern):
                    # 检查是否存在聚合操作（sum, mean, std等）在循环内部
                    if any(op in code_snippet for op in self.recommended_operations):
                        location = LocationInfo(
                            file_path=pipeline.file_path,
                            line_number=node.line_number,
                            column_number=getattr(node, 'column_number', -1)
                        )
                        
                        description = (
                            f"检测到低效的逐行聚合操作。"
                            f"建议使用向量化操作（如 df.groupby().sum()）替代循环遍历。"
                        )
                        
                        instance = SmellInstance(
                            smell_type=INEFFICIENT_AGGREGATION.name,
                            location=location,
                            description=description,
                            severity=SeverityLevel.HIGH,
                            affected_node_ids=[node.id]
                        )
                        
                        instances.append(instance)
                        break
        
        return instances
    
    def _match_pattern(self, code: str, pattern: str) -> bool:
        """简单的模式匹配
        
        Args:
            code: 代码片段
            pattern: 正则表达式模式
            
        Returns:
            是否匹配
        """
        import re
        try:
            return bool(re.search(pattern, code, re.IGNORECASE))
        except re.error:
            return False


class UnnecessaryMaterializationDetector(SmellDetector):
    """不必要的中间结果持久化检测器
    
    检测不必要的中间DataFrame持久化操作，如频繁的write_csv或pickle保存。
    这会显著影响性能，尤其是对于大数据集。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义不必要的持久化操作
        self.materialization_operations = {
            'to_csv',
            'to_pickle',
            'to_parquet',
            'to_feather',
            'to_hdf',
            'save'
        }
        # 定义可能的临时数据名称模式
        self.temp_patterns = ['temp', 'intermediate', 'tmp']
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline中不必要的中间结果持久化
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        nodes = pipeline.get_nodes()
        materialization_count = 0
        
        for node in nodes:
            operation = node.operation_type.lower()
            
            # 检查是否是持久化操作
            if any(mat_op in operation for mat_op in self.materialization_operations):
                var_name = node.outputs[0].lower() if node.outputs else ""
                
                # 检查是否是临时数据
                is_temp = any(temp in var_name for temp in self.temp_patterns)
                
                # 检查该节点是否有后继节点（即是否被后续操作使用）
                successors = pipeline.get_successors(node.id)
                
                # 如果是临时数据且无后继节点，可能是不必要的持久化
                if is_temp and len(successors) == 0:
                    location = LocationInfo(
                        file_path=pipeline.file_path,
                        line_number=node.line_number,
                        column_number=getattr(node, 'column_number', -1)
                    )
                    
                    description = (
                        f"检测到不必要的中间结果持久化：{var_name}。"
                        f"该临时数据未被后续操作使用，建议移除此持久化操作以提升性能。"
                    )
                    
                    instance = SmellInstance(
                        smell_type=UNNECESSARY_MATERIALIZATION.name,
                        location=location,
                        description=description,
                        severity=SeverityLevel.MEDIUM,
                        affected_node_ids=[node.id]
                    )
                    
                    instances.append(instance)
                
                materialization_count += 1
        
        # 如果Pipeline中有过多的持久化操作（>3次），也报告为潜在问题
        if materialization_count > 3:
            for node in nodes:
                operation = node.operation_type.lower()
                if any(mat_op in operation for mat_op in self.materialization_operations):
                    location = LocationInfo(
                        file_path=pipeline.file_path,
                        line_number=node.line_number,
                        column_number=getattr(node, 'column_number', -1)
                    )
                    
                    description = (
                        f"Pipeline包含过多的持久化操作（{materialization_count}次）。"
                        f"频繁的I/O操作会严重影响性能，建议考虑使用Pipeline链式操作替代中间持久化。"
                    )
                    
                    instance = SmellInstance(
                        smell_type=UNNECESSARY_MATERIALIZATION.name,
                        location=location,
                        description=description,
                        severity=SeverityLevel.HIGH,
                        affected_node_ids=[node.id]
                    )
                    
                    instances.append(instance)
                    break  # 只报告一次
        
        return instances


class LargeDataFrameOperationDetector(SmellDetector):
    """大数据集低效操作检测器
    
    检测对大DataFrame的全量操作，如遍历所有行、对整个DataFrame进行复杂操作。
    这可能导致性能问题和内存溢出。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义可能的全量操作模式
        self.full_scan_patterns = [
            'for.*in.*df[:]',  # 遍历所有行
            'df.apply.*axis=1',  # 对所有行 apply
            'df.iterrows',  # 显式遍历行
        ]
        # 定义大DataFrame的阈值（行数）
        self.large_df_threshold = 100000
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline中的大DataFrame低效操作
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        nodes = pipeline.get_nodes()
        
        for node in nodes:
            code_snippet = node.code_snippet.lower()
            
            # 检查是否存在全量扫描模式
            for pattern in self.full_scan_patterns:
                if self._match_pattern(code_snippet, pattern):
                    # 检查是否对大DataFrame操作（通过变量名或形状推断）
                    if self._is_potentially_large_data(code_snippet):
                        location = LocationInfo(
                            file_path=pipeline.file_path,
                            line_number=node.line_number,
                            column_number=getattr(node, 'column_number', -1)
                        )
                        
                        description = (
                            f"检测到对大DataFrame的全量操作。"
                            f"遍历所有行可能会严重影响性能，建议使用向量化操作或分块处理。"
                        )
                        
                        instance = SmellInstance(
                            smell_type=LARGE_DATAFRAME_OPERATION.name,
                            location=location,
                            description=description,
                            severity=SeverityLevel.HIGH,
                            affected_node_ids=[node.id]
                        )
                        
                        instances.append(instance)
                        break
        
        return instances
    
    def _match_pattern(self, code: str, pattern: str) -> bool:
        """简单的模式匹配
        
        Args:
            code: 代码片段
            pattern: 正则表达式模式
            
        Returns:
            是否匹配
        """
        import re
        try:
            return bool(re.search(pattern, code, re.IGNORECASE))
        except re.error:
            return False
    
    def _is_potentially_large_data(self, code: str) -> bool:
        """判断是否可能是大DataFrame操作
        
        Args:
            code: 代码片段
            
        Returns:
            是否可能是大DataFrame
        """
        # 简单启发式：如果包含'df'或'data'等变量名，且无明确的小样本限制
        large_keywords = ['df', 'data', 'dataset']
        sample_keywords = ['sample', 'head', '[:10]', '[:100]']
        
        has_large_data = any(keyword in code for keyword in large_keywords)
        is_sample = any(keyword in code for keyword in sample_keywords)
        
        return has_large_data and not is_sample
