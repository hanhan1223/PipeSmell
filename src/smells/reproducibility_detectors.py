"""
可复现性类Smell检测器模块

提供针对Pipeline可复现性问题的检测器，包括硬编码参数、缺少版本固定和非确定性操作。
所有检测器都继承自SmellDetector基类，实现可复现性相关的检测逻辑。
"""

import re
from typing import List, Set

from src.core.pipeline import PipelineGraph, PipelineNode
from src.core.logger import Logger
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import (
    HARDCODED_PARAMETERS,
    LACK_OF_VERSION_CONTROL,
    NON_DETERMINISTIC_ORDER,
    SeverityLevel
)


class HardcodedParametersDetector(SmellDetector):
    """硬编码参数检测器
    
    检测硬编码的超参数和配置值，如直接在代码中写死的数值字符串。
    这会降低代码的可移植性和可复现性。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义常见的超参数名称
        self.hyperparameter_names = {
            'n_estimators', 'max_depth', 'learning_rate', 'random_state',
            'test_size', 'train_size', 'batch_size', 'epochs',
            'alpha', 'lambda', 'C', 'kernel', 'verbose'
        }
        # 定义需要版本控制的库
        self.libraries_to_version = [
            'pandas', 'numpy', 'scikit-learn', 'sklearn', 'torch', 
            'tensorflow', 'keras', 'matplotlib', 'seaborn', 'xgboost'
        ]
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline中的硬编码参数
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        nodes = pipeline.get_nodes()
        
        for node in nodes:
            # 检查节点代码中是否有超参数赋值
            if self._contains_hardcoded_hyperparams(node.code_snippet):
                location = LocationInfo(
                    file_path=pipeline.file_path,
                    line_number=node.line_number,
                    column_number=getattr(node, 'column_number', -1)
                )
                
                description = (
                    f"检测到硬编码的超参数。"
                    f"建议将超参数提取到配置文件或参数字典中，以提高可维护性和可复现性。"
                )
                
                instance = SmellInstance(
                    smell_type=HARDCODED_PARAMETERS.name,
                    location=location,
                    description=description,
                    severity=SeverityLevel.MEDIUM,
                    affected_node_ids=[node.id]
                )
                
                instances.append(instance)
        
        # 检查整个文件的硬编码字符串（如路径、文件名等）
        file_content = pipeline.get_file_content()
        hardcoded_strings = self._detect_hardcoded_strings(file_content)
        
        if hardcoded_strings:
            for line_num, string_value in hardcoded_strings:
                location = LocationInfo(
                    file_path=pipeline.file_path,
                    line_number=line_num,
                    column_number=-1
                )
                
                description = (
                    f"检测到硬编码字符串：'{string_value}'。"
                    f"建议提取为配置参数。"
                )
                
                instance = SmellInstance(
                    smell_type=HARDCODED_PARAMETERS.name,
                    location=location,
                    description=description,
                    severity=SeverityLevel.LOW,
                    affected_node_ids=[]
                )
                
                instances.append(instance)
        
        return instances
    
    def _contains_hardcoded_hyperparams(self, code: str) -> bool:
        """检查代码是否包含硬编码的超参数
        
        Args:
            code: 代码片段
            
        Returns:
            是否包含硬编码超参数
        """
        code_lower = code.lower()
        
        # 检查常见的超参数赋值模式
        pattern = r'\b(' + '|'.join(self.hyperparameter_names) + r')\s*=\s*[0-9]+(?:\.[0-9]+)?'
        
        try:
            matches = re.finditer(pattern, code_lower, re.IGNORECASE)
            for match in matches:
                # 检查赋值的值是否是字面量（不是变量引用）
                value_part = code[match.end():]
                value_start = 0
                while value_start < len(value_part) and value_part[value_start] in ' \t':
                    value_start += 1
                
                if value_start < len(value_part) and value_part[value_start] in '0123456789':
                    return True
        except re.error:
            pass
        
        return False
    
    def _detect_hardcoded_strings(self, code: str) -> List[tuple]:
        """检测硬编码的字符串（路径、URL等）
        
        Args:
            code: 完整代码
            
        Returns:
            硬编码字符串列表 [(line_num, string_value), ...]
        """
        hardcoded_strings = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # 检查常见的硬编码模式
            patterns = [
                r'["\']([a-zA-Z]:[/\\][^"\']+)["\']',  # Windows路径
                r'["\']([/][^"\']+)["\']',  # Unix路径
                r'["\'](https?://[^"\']+)["\']',  # URL
            ]
            
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        string_value = match.group(1)
                        hardcoded_strings.append((line_num, string_value))
                except re.error:
                    pass
        
        return hardcoded_strings


class LackOfVersionControlDetector(SmellDetector):
    """缺少版本控制检测器
    
    检测是否缺少库版本固定，如requirements.txt或pip freeze输出。
    缺少版本控制会导致不同环境下的行为不一致。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 检查是否在requirements.txt或同等文件中
        self.version_files = ['requirements.txt', 'environment.yml', 'Pipfile', 'setup.py']
        self.libraries_to_version = [
            'pandas', 'numpy', 'scikit-learn', 'sklearn', 'torch', 
            'tensorflow', 'keras', 'matplotlib', 'seaborn', 'xgboost'
        ]
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测是否缺少库版本固定
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        import os
        
        # 检查是否在同一个目录下存在requirements.txt等文件
        project_dir = os.path.dirname(pipeline.file_path)
        has_version_file = False
        
        for version_file in self.version_files:
            version_file_path = os.path.join(project_dir, version_file)
            if os.path.exists(version_file_path):
                has_version_file = True
                break
        
        if not has_version_file:
            locations = self._find_import_locations(pipeline)
            
            if locations:
                # 在第一个import语句处报告
                first_location = locations[0]
                
                description = (
                    f"项目缺少库版本固定文件（如requirements.txt）。"
                    f"缺少版本控制会导致不同环境下的行为不一致，建议添加版本固定文件。"
                )
                
                instance = SmellInstance(
                    smell_type=LACK_OF_VERSION_CONTROL.name,
                    location=first_location,
                    description=description,
                    severity=SeverityLevel.HIGH,
                    affected_node_ids=[]
                )
                
                instances.append(instance)
        
        return instances
    
    def _find_import_locations(self, pipeline: 'PipelineGraph') -> List[LocationInfo]:
        """找到import语句的位置
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            import语句的位置列表
        """
        locations = []
        file_content = pipeline.get_file_content()
        lines = file_content.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            line_stripped = line.strip()
            
            # 检查是否是import语句
            if line_stripped.startswith('import ') or line_stripped.startswith('from '):
                # 检查是否导入了需要版本控制的库
                for lib in self.libraries_to_version:
                    if lib in line_stripped:
                        location = LocationInfo(
                            file_path=pipeline.file_path,
                            line_number=line_num,
                            column_number=-1
                        )
                        locations.append(location)
                        break
        
        return locations


class NonDeterministicOrderDetector(SmellDetector):
    """非确定性顺序检测器
    
    检测使用无序数据结构（如set、dict）的迭代操作。
    这可能导致Pipeline执行顺序不一致。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义无序数据结构类型
        self.unordered_types = ['set', 'dict']
        # 可能导致非确定性的迭代模式
        self.iteration_patterns = [
            r'for\s+\w+\s+in\s+(\w+)',  # 基本循环
            r'tuple\(\?\w+\)',  # 转换为无序类型
        ]
    
    def detect(self, pipeline: 'PipelineGraph') -> 'List[SmellInstance]':
        """检测Pipeline中的非确定性顺序操作
        
        Args:
            pipeline: Pipeline图对象
            
        Returns:
            检测到的Smell实例列表
        """
        instances = []
        nodes = pipeline.get_nodes()
        
        for node in nodes:
            code_snippet = node.code_snippet
            
            # 检查是否在对无序数据结构进行迭代
            if self._contains_unordered_iteration(code_snippet):
                location = LocationInfo(
                    file_path=pipeline.file_path,
                    line_number=node.line_number,
                    column_number=getattr(node, 'column_number', -1)
                )
                
                description = (
                    f"检测到对无序数据结构（set/dict）的迭代操作。"
                    f"这可能导致Pipeline执行顺序不一致，建议对数据结构进行排序或使用有序类型。"
                )
                
                instance = SmellInstance(
                    smell_type=NON_DETERMINISTIC_ORDER.name,
                    location=location,
                    description=description,
                    severity=SeverityLevel.MEDIUM,
                    affected_node_ids=[node.id]
                )
                
                instances.append(instance)
        
        return instances
    
    def _contains_unordered_iteration(self, code: str) -> bool:
        """检查代码是否包含对无序数据结构的迭代
        
        Args:
            code: 代码片段
            
        Returns:
            是否包含非确定性迭代
        """
        code_lower = code.lower()
        
        # 检查是否在for循环中迭代set或dict
        for pattern in self.iteration_patterns:
            try:
                matches = re.finditer(pattern, code_lower, re.IGNORECASE)
                for match in matches:
                    # 获取被迭代的变量名
                    loop_var = match.group(1)
                    
                    # 检查该变量是否是set或dict类型
                    # 简化版：检查变量赋值语句
                    assignment_pattern = rf'\b{loop_var}\s*=\s*\w+\('
                    assignment_matches = re.finditer(assignment_pattern, code_lower, re.IGNORECASE)
                    
                    for assign_match in assignment_matches:
                        assign_prefix = code_lower[:assign_match.start()]
                        # 查找前面的函数调用
                        for utype in self.unordered_types:
                            if f'{utype}(' in assign_prefix[-50:]:
                                return True
            except re.error:
                pass
        
        return False
