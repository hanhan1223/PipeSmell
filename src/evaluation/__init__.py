"""
评估框架模块

提供完整的评估功能，包括：
- Ground Truth匹配
- 评估指标计算
- 统计显著性检验
- 结果可视化
"""

from src.evaluation.matcher import (
    GroundTruthMatcher,
    MatchStrategy,
    SmellMatch,
    MatchingResult,
    BatchMatcher
)

from src.evaluation.metrics import (
    ConfusionMatrix,
    MetricsResult,
    MetricsCalculator,
    RankingMetrics,
    calculate_cohen_kappa
)

from src.evaluation.evaluator import (
    EvaluationConfig,
    EvaluationResult,
    Evaluator,
    GroundTruthLoader
)

from src.evaluation.statistical_tests import (
    StatisticalTests,
    MultiMethodComparison
)

__all__ = [
    # Matcher
    'GroundTruthMatcher',
    'MatchStrategy',
    'SmellMatch',
    'MatchingResult',
    'BatchMatcher',
    
    # Metrics
    'ConfusionMatrix',
    'MetricsResult',
    'MetricsCalculator',
    'RankingMetrics',
    'calculate_cohen_kappa',
    
    # Evaluator
    'EvaluationConfig',
    'EvaluationResult',
    'Evaluator',
    'GroundTruthLoader',
    
    # Statistical Tests
    'StatisticalTests',
    'MultiMethodComparison'
]
