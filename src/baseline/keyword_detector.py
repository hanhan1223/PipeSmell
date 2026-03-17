"""
关键词检测基线模块

实现基于关键词的简单Smell检测（Baseline 1）。
使用正则表达式模式匹配快速检测常见的Pipeline Smell。
"""

import re
from typing import Dict, List, Optional, Tuple

from src.core.parser import ASTParser, APIExtractor
from src.core.logger import Logger
from src.smells.detector import LocationInfo, SmellInstance, DetectionResult
from src.smells.taxonomy import (
    DATA_LEAKAGE,
    HARDCODED_PARAMETERS,
    MISSING_RANDOM_SEED,
    SeverityLevel,
)


class KeywordBaseline:
    """关键词检测基线
    
    基于预定义的正则表达式模式快速检测Pipeline Smell。
    这是Baseline 1，用于与本方法的Pipeline-aware detection进行对比。
    """
    
    def __init__(self):
        """初始化关键词检测基线"""
        self.parser = ASTParser()
        self.logger = Logger.setup('KeywordBaseline', 'logs/baseline.log', 'INFO')
        
        # 定义检测模式字典
        # 格式: {Smell类型: (正则表达式, 严重性, 描述)}
        self.patterns = {
            DATA_LEAKAGE.name: (
                r'(StandardScaler\.(fit_transform|fit|transform).*\n.*train_test_split|'
                r'MinMaxScaler\.(fit_transform|fit|transform).*\n.*train_test_split|'
                r'RobustScaler\.(fit_transform|fit|transform).*\n.*train_test_split|'
                r'SimpleImputer\.(fit_transform|fit|transform).*\n.*train_test_split)',
                SeverityLevel.CRITICAL,
                "检测到可能在train_test_split之前进行了数据标准化操作，可能导致数据泄露"
            ),
            HARDCODED_PARAMETERS.name: (
                r'(n_estimators|max_depth|min_samples_split|min_samples_leaf|'
                r'learning_rate|C|alpha|gamma|kernel)\s*=\s*\d+',
                SeverityLevel.MEDIUM,
                "检测到硬编码的超参数值，建议使用配置文件或超参数调优"
            ),
            MISSING_RANDOM_SEED.name: (
                r'train_test_split\([^)]*\)(?!.*random_state\b)',
                SeverityLevel.HIGH,
                "检测到train_test_split未设置random_state参数，可能导致结果不可复现"
            ),
            'MISSING_EVALUATION': (
                r'model\.fit\(.*\)(?!.*\.(predict|score|evaluate))',
                SeverityLevel.MEDIUM,
                "检测到模型训练后缺少评估步骤"
            ),
            'EXCESSIVE_COPY': (
                r'\.copy\(\)(.*\n){0,10}\.copy\(\)',
                SeverityLevel.LOW,
                "检测到连续的数据复制操作"
            ),
        }
        
        # 预编译正则表达式
        self.compiled_patterns = {
            name: (re.compile(pattern, re.MULTILINE | re.DOTALL), severity, desc)
            for name, (pattern, severity, desc) in self.patterns.items()
        }
        
        self.logger.info(f"KeywordBaseline初始化完成，加载了{len(self.patterns)}个检测模式")
    
    def detect(self, file_path: str) -> List[SmellInstance]:
        """检测文件中的Pipeline Smell
        
        读取源文件内容，对每个pattern应用正则匹配。
        若匹配则生成SmellInstance（记录匹配内容和位置）。
        
        Args:
            file_path: Python文件路径
            
        Returns:
            检测到的Smell实例列表，每个实例代表一处匹配的Smell
        """
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 读取文件行用于定位
            lines = code.split('\n')
            detected_smells = []
            
            # 对每个模式进行匹配
            for smell_type, (pattern, severity, description) in self.compiled_patterns.items():
                matches = pattern.finditer(code)
                
                for match in matches:
                    # 计算匹配位置
                    line_number = code[:match.start()].count('\n') + 1
                    column = match.start() - code.rfind('\n', 0, match.start()) - 1
                    
                    # 提取匹配的代码片段
                    matched_text = match.group()
                    snippet_start = max(0, match.start() - 50)
                    snippet_end = min(len(code), match.end() + 50)
                    code_snippet = code[snippet_start:snippet_end]
                    
                    # 生成修复建议
                    suggestion = self._get_suggestion(smell_type)
                    
                    # 创建Smell实例
                    location = LocationInfo(
                        file_path=file_path,
                        line_number=line_number,
                        column=column,
                        code_snippet=code_snippet
                    )
                    
                    smell = SmellInstance(
                        smell_type=smell_type,
                        location=location,
                        description=description,
                        severity=severity.value,
                        affected_nodes=[],
                        suggestion=suggestion
                    )
                    
                    detected_smells.append(smell)
                    
                    self.logger.debug(
                        f"匹配到Smell: {smell_type} 在 {file_path}:{line_number}"
                    )
            
            self.logger.info(f"关键词检测完成，找到 {len(detected_smells)} 个Smell")
            return detected_smells
            
        except FileNotFoundError:
            self.logger.error(f"文件未找到: {file_path}")
            return []
        except Exception as e:
            self.logger.error(f"检测过程中出错: {e}")
            return []
    
    def _get_suggestion(self, smell_type: str) -> str:
        """获取Smell类型的修复建议
        
        Args:
            smell_type: Smell类型名称
            
        Returns:
            修复建议字符串
        """
        suggestions = {
            DATA_LEAKAGE.name: (
                "确保标准化操作只在训练集上执行，然后应用于测试集。"
                "建议在train_test_split之后分别对训练集和测试集进行标准化。"
            ),
            HARDCODED_PARAMETERS.name: (
                "建议将超参数提取到配置文件中，或使用GridSearchCV、RandomizedSearchCV"
                "等工具进行超参数调优。"
            ),
            MISSING_RANDOM_SEED.name: (
                "在train_test_split或其他随机操作中添加random_state参数，"
                "例如: train_test_split(X, y, random_state=42)"
            ),
            'MISSING_EVALUATION': (
                "在模型训练后添加评估步骤，使用accuracy_score、precision_score等指标"
                "或使用cross_val_score进行交叉验证。"
            ),
            'EXCESSIVE_COPY': (
                "检查是否真的需要数据副本，考虑使用引用传递或只在必要时使用.copy()。"
            ),
        }
        return suggestions.get(smell_type, "请review代码并根据最佳实践修正此问题")
    
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
        
        # 构建Pipeline信息（基线方法无法获取详细信息）
        pipeline_info = {
            'file_path': file_path,
            'num_nodes': 'N/A',
            'num_modules': 'N/A',
            'num_edges': 'N/A',
            'method': 'KeywordBaseline'
        }
        
        result = DetectionResult(
            pipeline_info=pipeline_info,
            detected_smells=smells,
            runtime_ms=0  # 基线方法通常很快，不记录时间
        )
        
        return result
    
    def get_supported_smell_types(self) -> List[str]:
        """获取支持的Smell类型列表
        
        Returns:
            Smell类型名称列表
        """
        return list(self.patterns.keys())
