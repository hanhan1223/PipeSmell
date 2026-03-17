"""
SonarQube基线适配器模块

模拟SonarQube的检测结果（Baseline 3）。
将SonarQube规则映射到Pipeline Smell。
"""

import time
from typing import Dict, List

from src.core.logger import Logger
from src.smells.detector import LocationInfo, SmellInstance, DetectionResult
from src.smells.taxonomy import (
    EXCESSIVE_COPY,
    REDUNDANT_OPERATION,
    HARDCODED_PARAMETERS,
    SeverityLevel,
)


class SonarQubeBaseline:
    """SonarQube基线适配器
    
    模拟SonarQube的检测结果，将SonarQube规则映射到Pipeline Smell。
    这是Baseline 3，提供基于静态代码分析工具的结果。
    """
    
    def __init__(self):
        """初始化SonarQube基线适配器"""
        self.logger = Logger.setup('SonarQubeBaseline', 'logs/baseline.log', 'INFO')
        
        # 映射SonarQube规则ID到Pipeline Smell
        # 格式: {SonarQube规则ID: (Smell类型, 严重性)}
        self.sonarqube_rules = {
            'python:S1134': (HARDCODED_PARAMETERS.name, SeverityLevel.MEDIUM),
            'python:S1172': (REDUNDANT_OPERATION.name, SeverityLevel.LOW),
            'python:S1172': (EXCESSIVE_COPY.name, SeverityLevel.LOW),
            'python:S1481': (REDUNDANT_OPERATION.name, SeverityLevel.LOW),
            'python:S107': (HARDCODED_PARAMETERS.name, SeverityLevel.LOW),
            'python:python:S1135': (EXCESSIVE_COPY.name, SeverityLevel.LOW),
        }
        
        # 模拟的问题模板
        self.issue_templates = {
            HARDCODED_PARAMETERS.name: {
                'message': '硬编码的参数值应该被提取到命名常量中',
                'rule': 'python:S1134'
            },
            REDUNDANT_OPERATION.name: {
                'message': '移除此条未使用的或冗余的代码',
                'rule': 'python:S1172'
            },
            EXCESSIVE_COPY.name: {
                'message': '不必要的数据复制操作',
                'rule': 'python:S1481'
            },
        }
        
        self.logger.info(f"SonarQubeBaseline初始化完成，加载了{len(self.sonarqube_rules)}个规则")
    
    def detect(self, file_path: str) -> List[SmellInstance]:
        """模拟调用SonarQube API进行检测
        
        模拟调用SonarQube API（或基于静态规则直接映射），
        对每个检查出的SonarQube问题转换对应的Pipeline Smell，
        生成SmellInstance。
        
        Args:
            file_path: Python文件路径
            
        Returns:
            检测到的Smell实例列表
        """
        try:
            # 在实际应用中，这里会调用SonarQube Web API或CLI工具
            # 这里我们模拟一些检测结果
            simulated_issues = self._simulate_sonarqube_scan(file_path)
            
            # 转换为Smell实例
            detected_smells = []
            for issue in simulated_issues:
                smell = self._convert_result(issue)
                if smell:
                    smell.location.file_path = file_path
                    detected_smells.append(smell)
                    self.logger.debug(
                        f"SonarQube问题 {issue['rule_id']} 转换为 Smell: {smell.smell_type}"
                    )
            
            self.logger.info(f"SonarQube检测完成（模拟），找到 {len(detected_smells)} 个Smell")
            return detected_smells
            
        except Exception as e:
            self.logger.error(f"SonarQube检测过程中出错: {e}")
            return []
    
    def _simulate_sonarqube_scan(self, file_path: str) -> List[Dict]:
        """模拟SonarQube扫描结果
        
        在实际应用中，这里会解析SonarQube API的JSON响应。
        这里我们生成一些模拟的问题报告。
        
        Args:
            file_path: 文件路径
            
        Returns:
            模拟的SonarQube问题列表
        """
        # 读取文件获取一些上下文信息
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                lines = code.split('\n')
        except:
            lines = []
        
        # 模拟发现的问题
        simulated_issues = []
        
        # 随机选择一些行号作为问题位置
        if lines:
            import random
            random.seed(42)  # 固定随机种子以获得可复现的结果
            
            potential_lines = [i for i in range(1, min(len(lines), 50)) if i % 10 == 0]
            
            for line_num in potential_lines:
                # 为每个位置随机分配一个问题类型
                issue_template = random.choice(list(self.issue_templates.values()))
                
                simulated_issues.append({
                    'rule_id': issue_template['rule'],
                    'line': line_num,
                    'message': issue_template['message'],
                    'severity': 'MINOR' if random.random() > 0.5 else 'MAJOR',
                    'code_snippet': lines[line_num - 1] if line_num <= len(lines) else '',
                })
        
        return simulated_issues
    
    def _convert_result(self, sonarqube_issue: Dict) -> SmellInstance:
        """将SonarQube issue格式转换为标准SmellInstance
        
        Args:
            sonarqube_issue: SonarQube问题字典
            
        Returns:
            Smell实例对象
        """
        rule_id = sonarqube_issue.get('rule_id', '')
        
        # 查找对应的Smell类型
        if rule_id in self.sonarqube_rules:
            smell_type, severity = self.sonarqube_rules[rule_id]
        else:
            # 默认映射为冗余操作
            smell_type = REDUNDANT_OPERATION.name
            severity = SeverityLevel.LOW
        
        # 映射SonarQube严重性
        sonar_severity = sonarqube_issue.get('severity', 'MINOR')
        severity_mapping = {
            'CRITICAL': SeverityLevel.CRITICAL,
            'MAJOR': SeverityLevel.HIGH,
            'MINOR': SeverityLevel.MEDIUM,
            'INFO': SeverityLevel.LOW
        }
        mapped_severity = severity_mapping.get(sonar_severity, severity)
        
        # 创建位置信息
        location = LocationInfo(
            file_path='',  # 将在detect中设置
            line_number=sonarqube_issue.get('line', 0),
            column=0,
            code_snippet=sonarqube_issue.get('code_snippet', '')
        )
        
        # 生成描述和建议
        description = f"SonarQube规则 {rule_id}: {sonarqube_issue.get('message', '')}"
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
                "按照SonarQube建议，将硬编码值提取为命名常量或配置变量"
            ),
            REDUNDANT_OPERATION.name: (
                "移除未使用的或冗余的代码，保持代码简洁"
            ),
            EXCESSIVE_COPY.name: (
                "审查数据复制的必要性，避免不必要的内存使用"
            ),
        }
        return suggestions.get(smell_type, "请review代码并参考SonarQube的建议")
    
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
            'method': 'SonarQubeBaseline',
            'scanned_rules': len(self.sonarqube_rules)
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
        return list(set(smell_type for smell_type, _ in self.sonarqube_rules.values()))
