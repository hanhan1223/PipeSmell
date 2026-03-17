"""
基线方法模块

提供与Pipeline-aware Detection进行对比的基线实现。
包含关键词检测、启发式规则、SonarQube和PMD适配器。
"""

from .keyword_detector import KeywordBaseline
from .heuristic_detector import HeuristicBaseline
from .sonarqube_adapter import SonarQubeBaseline
from .pmd_adapter import PMDBaseline

__all__ = [
    'KeywordBaseline',
    'HeuristicBaseline',
    'SonarQubeBaseline',
    'PMDBaseline'
]
