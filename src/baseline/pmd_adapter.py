"""
PMD基线适配器模块

模拟PMD的检测结果（Baseline 4）。
将PMD规则映射到Pipeline Smell。
"""

import time
from typing import Dict, List

from src.core.logger import Logger
from src.smells.detector import LocationInfo, SmellInstance, DetectionResult
from src.smells.taxonomy import (
    EXCESSIVE_COPY,
    HARDCODED_PARAMETERS,
    REDUNDANT_OPERATION,
    LACK_OF_VERSION_CONTROL,
    SeverityLevel,
)


class PMDBaseline:
    """PMD基线适配器
    
    模拟PMD的检测结果，将PMD规则映射到Pipeline Smell。
    这是Baseline 4，提供基于静态代码分析工具的结果。
    """
    
    def __init__(self):
        """初始化PMD基线适配器"""
        self.logger = Logger.setup('PMDBaseline', 'logs/baseline.log', 'INFO')
        
        # 映射PMD规则key到Pipeline Smell
        # 格式: {PMD规则: (Smell类型, 严重性)}
        self.pmd_rules = {
            'AvoidUsingHardCodedValues': (HARDCODED_PARAMETERS.name, SeverityLevel.MEDIUM),
            'SimplifyBooleanReturns': (REDUNDANT_OPERATION.name, SeverityLevel.LOW),
            'UselessOperationOnImmutable': (REDUNDANT_OPERATION.name, SeverityLevel.LOW),
            'AvoidCatchingGenericException': (HARDCODED_PARAMETERS.name, SeverityLevel.MEDIUM),
            'DataflowAnomalyAnalysis': (REDUNDANT_OPERATION.name, SeverityLevel.HIGH),
            'CloneMethodMustImplementCloneable': (EXCESSIVE_COPY.name, SeverityLevel.LOW),
            'ExcessiveImports': (REDUNDANT_OPERATION.name, SeverityLevel.LOW),
            'DuplicateImports': (REDUNDANT_OPERATION.name, SeverityLevel.LOW),
            'MissingVersionControlCheck': (LACK_OF_VERSION_CONTROL.name, SeverityLevel.MEDIUM),
        }
        
        # PMD违规模板
        self.violation_templates = {
            HARDCODED_PARAMETERS.name: {
                'rule': 'AvoidUsingHardCodedValues',
                'message': '避免使用硬编码值，应该使用常量或配置'
            },
            REDUNDANT_OPERATION.name: {
                'rule': 'SimplifyBooleanReturns',
                'message': '简化布尔返回语句，移除冗余操作'
            },
            EXCESSIVE_COPY.name: {
                'rule': 'CloneMethodMustImplementCloneable',
                'message': '检查数据复制的必要性'
            },
            LACK_OF_VERSION_CONTROL.name: {
                'rule': 'MissingVersionControlCheck',
                'message': '缺少版本控制检查'
            },
        }
        
        self.logger.info(f"PMDBaseline初始化完成，加载了{len(self.pmd_rules)}个规则")
    
    def detect(self, file_path: str) -> List[SmellInstance]:
        """模拟调用PMD检测API进行检测
        
        模拟调用PMD检测API，将PMD规则违规转换为Pipeline Smell，
        生成SmellInstance。
        
        Args:
            file_path: Python文件路径
            
        Returns:
            检测到的Smell实例列表
        """
        try:
            # 在实际应用中，这里会调用PMD命令行工具或解析PMD XML报告
            # 这里我们模拟一些检测结果
            simulated_violations = self._simulate_pmd_scan(file_path)
            
            # 转换为Smell实例
            detected_smells = []
            for violation in simulated_violations:
                smell = self._convert_result(violation)
                if smell:
                    smell.location.file_path = file_path
                    detected_smells.append(smell)
                    self.logger.debug(
                        f"PMD违规 {violation['rule']} 转换为 Smell: {smell.smell_type}"
                    )
            
            self.logger.info(f"PMD检测完成（模拟），找到 {len(detected_smells)} 个Smell")
            return detected_smells
            
        except Exception as e:
            self.logger.error(f"PMD检测过程中出错: {e}")
            return []
    
    def _simulate_pmd_scan(self, file_path: str) -> List[Dict]:
        """模拟PMD扫描结果
        
        在实际应用中，这里会解析PMD XML或JSON报告。
        这里我们生成一些模拟的违规记录。
        
        Args:
            file_path: 文件路径
            
        Returns:
            模拟的PMD违规列表
        """
        # 读取文件获取一些上下文信息
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                lines = code.split('\n')
        except:
            lines = []
        
        # 模拟发现的违规
        simulated_violations = []
        
        if lines:
            import random
            random.seed(43)  # 固定随机种子
            
            # 随机选择一些行号作为违规位置
            potential_lines = [i for i in range(1, min(len(lines), 50)) if i % 8 == 0]
            
            for line_num in potential_lines:
                # 为每个位置随机分配一个违规类型
                violation_template = random.choice(list(self.violation_templates.values()))
                
                # 随机确定优先级
                priorities = ['1', '2', '3', '4', '5']
                priority = random.choice(priorities)
                
                simulated_violations.append({
                    'rule': violation_template['rule'],
                    'line': line_num,
                    'priority': priority,
                    'message': violation_template['message'],
                    'code_snippet': lines[line_num - 1] if line_num <= len(lines) else '',
                    'external_info_url': f"https://pmd.github.io/pmd-{priority}/rules/{violation_template['rule']}.html"
                })
        
        return simulated_violations
    
    def _convert_result(self, pmd_violation: Dict) -> SmellInstance:
        """将PMD违规格式转换为标准SmellInstance
        
        Args:
            pmd_violation: PMD违规字典
            
        Returns:
            Smell实例对象
        """
        rule = pmd_violation.get('rule', '')
        
        # 查找对应的Smell类型
        if rule in self.pmd_rules:
            smell_type, severity = self.pmd_rules[rule]
        else:
            # 默认映射为冗余操作
            smell_type = REDUNDANT_OPERATION.name
            severity = SeverityLevel.LOW
        
        # 映射PMD优先级到严重性
        pmd_priority = pmd_violation.get('priority', '3')
        priority_mapping = {
            '1': SeverityLevel.CRITICAL,
            '2': SeverityLevel.HIGH,
            '3': SeverityLevel.MEDIUM,
            '4': SeverityLevel.LOW,
            '5': SeverityLevel.LOW
        }
        mapped_severity = priority_mapping.get(pmd_priority, severity)
        
        # 创建位置信息
        location = LocationInfo(
            file_path='',  # 将在detect中设置
            line_number=pmd_violation.get('line', 0),
            column=0,
            code_snippet=pmd_violation.get('code_snippet', '')
        )
        
        # 生成描述和建议
        description = (
            f"PMD规则 {rule} (Priority {pmd_priority}): "
            f"{pmd_violation.get('message', '')}"
        )
        suggestion = self._get_suggestion(smell_type)
        
        return SmellInstance(
            smell_type=smell_type,
            location=location,
            description=description,
            severity=mapped_severity.value,
            affected_nodes=[],
            suggestion=suggestion
        )
    
    def _get_suggestion(self, smell_type: str) -> str:
        """获取Smell的修复建议
        
        Args:
            smell_type: Smell类型
            
        Returns:
            修复建议字符串
        """
        suggestions = {
            HARDCODED_PARAMETERS.name: (
                "按照PMD建议，将硬编码值提取为命名常量或配置变量"
            ),
            REDUNDANT_OPERATION.name: (
                "移除冗余的操作，简化代码逻辑以提高可读性"
            ),
            EXCESSIVE_COPY.name: (
                "审查数据复制的必要性，遵循DRY原则"
            ),
            LACK_OF_VERSION_CONTROL.name: (
                "添加版本控制检查，确保代码在不同环境下的兼容性"
            ),
        }
        return suggestions.get(smell_type, "请review代码并参考PMD的建议")
    
    def convert_to_detection_result(self, file_path: str, 
                                  smells: List[SmellInstance]) -> DetectionResult:
        """将基线结果转换为标准DetectionResult格式
        
        Args:
            file_path: 文件路径
            smells: Smell实例列表
            
        Returns:
            标准格式的检测结果对象
        """
        import time
        
        pipeline_info = {
            'file_path': file_path,
            'num_nodes': 'N/A',
            'num_modules': 'N/A',
            'num_edges': 'N/A',
            'method': 'PMDBaseline',
            'scanned_rules': len(self.pmd_rules)
        }
        
        result = DetectionResult(
            pipeline_info=pipeline_info,
            detected_smells=smells,
            runtime_ms=0
        )
        
        return result
    
    def get_supported_smell_types(self) -> List[str]:
        """获取支持的Smell类型列表
        
        Returns:
            Smell类型名称列表
        """
        return list(set(smell_type for smell_type, _ in self.pmd_rules.values()))
