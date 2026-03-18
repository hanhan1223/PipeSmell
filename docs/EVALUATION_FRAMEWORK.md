# 评估框架文档

## 概述

本评估框架为Pipeline Smell Detection System提供完整的性能评估能力，支持：

- ✅ Ground Truth匹配（精确匹配、行范围匹配、语义匹配）
- ✅ 标准评估指标（Precision、Recall、F1-score）
- ✅ 统计显著性检验（t检验、Wilcoxon检验、效应量）
- ✅ 多方法对比分析
- ✅ 批量评估和结果聚合

## 架构设计

```
evaluation/
├── matcher.py              # Ground Truth匹配
│   ├── GroundTruthMatcher  # 单文件匹配器
│   ├── BatchMatcher        # 批量匹配器
│   └── MatchStrategy       # 匹配策略（EXACT, LINE_RANGE, SEMANTIC）
│
├── metrics.py              # 评估指标计算
│   ├── MetricsCalculator   # 指标计算器
│   ├── ConfusionMatrix     # 混淆矩阵
│   ├── RankingMetrics      # 排序指标（MAP, P@K, R@K）
│   └── calculate_cohen_kappa  # 标注一致性
│
├── evaluator.py            # 评估主流程
│   ├── Evaluator           # 评估器
│   ├── EvaluationConfig    # 评估配置
│   ├── EvaluationResult    # 评估结果
│   └── GroundTruthLoader   # 数据加载器
│
└── statistical_tests.py    # 统计检验
    ├── StatisticalTests    # 统计检验工具
    └── MultiMethodComparison  # 多方法比较
```

## 核心功能

### 1. Ground Truth匹配

支持三种匹配策略：

#### 精确匹配（EXACT）
```python
from src.evaluation import GroundTruthMatcher, MatchStrategy

matcher = GroundTruthMatcher(strategy=MatchStrategy.EXACT)
result = matcher.match(predictions, ground_truth)
```

要求：文件路径、行号、Smell类型完全一致

#### 行范围匹配（LINE_RANGE）
```python
matcher = GroundTruthMatcher(
    strategy=MatchStrategy.LINE_RANGE,
    line_tolerance=2  # 允许±2行误差
)
result = matcher.match(predictions, ground_truth)
```

适用场景：允许检测器报告的行号有小幅偏差

#### 语义匹配（SEMANTIC）
```python
matcher = GroundTruthMatcher(strategy=MatchStrategy.SEMANTIC)
result = matcher.match(predictions, ground_truth)
```

基于affected_nodes的Jaccard相似度，适用于跨行的Smell

### 2. 评估指标

#### 基础指标
```python
from src.evaluation import MetricsCalculator

# 二分类指标
metrics = MetricsCalculator.calculate_binary_metrics(
    predictions=pred_ids,
    ground_truth=gt_ids
)

print(f"Precision: {metrics.precision:.4f}")
print(f"Recall: {metrics.recall:.4f}")
print(f"F1-score: {metrics.f1_score:.4f}")
```

#### 多类别指标
```python
# 按Smell类型计算
per_smell_metrics = MetricsCalculator.calculate_per_smell_metrics(
    predictions=predictions,
    ground_truth=ground_truth
)

for smell_type, metrics in per_smell_metrics.items():
    print(f"{smell_type}: F1={metrics.f1_score:.4f}")
```

#### 排序指标
```python
from src.evaluation import RankingMetrics

# 平均精度均值
map_score = RankingMetrics.mean_average_precision(
    predictions=[(id, confidence), ...],
    ground_truth=gt_ids
)

# P@K和R@K
p_at_10 = RankingMetrics.precision_at_k(predictions, gt_ids, k=10)
r_at_10 = RankingMetrics.recall_at_k(predictions, gt_ids, k=10)
```

### 3. 完整评估流程

```python
from src.evaluation import Evaluator, EvaluationConfig, MatchStrategy

# 1. 配置评估参数
config = EvaluationConfig(
    match_strategy=MatchStrategy.LINE_RANGE,
    line_tolerance=2,
    output_dir="experiments/results",
    save_detailed_results=True,
    calculate_per_smell_metrics=True
)

# 2. 创建评估器
evaluator = Evaluator(config)

# 3. 执行评估
result = evaluator.evaluate(
    predictions=my_predictions,
    ground_truth=ground_truth,
    method_name="Pipeline-aware"
)

# 4. 查看结果
summary = result.get_summary()
print(f"F1-score: {summary['f1_score']:.4f}")
```

### 4. 批量评估

```python
# 按文件分组的数据
predictions_by_file = {
    'file1.py': [pred1, pred2, ...],
    'file2.py': [pred3, pred4, ...],
}

ground_truth_by_file = {
    'file1.py': [gt1, gt2, ...],
    'file2.py': [gt3, gt4, ...],
}

# 批量评估
result = evaluator.evaluate_batch(
    predictions_by_file=predictions_by_file,
    ground_truth_by_file=ground_truth_by_file,
    method_name="My Method"
)
```

### 5. 多方法比较

```python
# 评估多个方法
results = []

for method_name, predictions in all_methods.items():
    result = evaluator.evaluate(predictions, ground_truth, method_name)
    results.append(result)

# 生成比较报告
comparison = evaluator.compare_methods(results)

print(f"最佳方法: {comparison['best_method']}")
print(f"最佳F1: {comparison['best_f1']:.4f}")
```

### 6. 统计显著性检验

```python
from src.evaluation import StatisticalTests, MultiMethodComparison

# 配对t检验
t_test = StatisticalTests.paired_t_test(
    method1_scores=[0.85, 0.87, 0.89, ...],
    method2_scores=[0.78, 0.80, 0.82, ...],
    alpha=0.05
)

print(f"p-value: {t_test['p_value']:.4f}")
print(f"显著性: {t_test['is_significant']}")
print(f"更好的方法: {t_test['better_method']}")

# Wilcoxon检验（非参数）
wilcoxon = StatisticalTests.wilcoxon_test(
    method1_scores, method2_scores
)

# 效应量
effect_size = StatisticalTests.cohen_d(method1_scores, method2_scores)
interpretation = StatisticalTests.interpret_effect_size(effect_size)

print(f"Cohen's d: {effect_size:.4f} ({interpretation})")

# 多方法比较
comparison_tool = MultiMethodComparison(alpha=0.05)

method_scores = {
    'Pipeline-aware': [0.85, 0.87, 0.89, ...],
    'Baseline-Keyword': [0.65, 0.67, 0.69, ...],
    'Baseline-Heuristic': [0.75, 0.77, 0.79, ...],
}

results = comparison_tool.compare_all(method_scores)

# 生成Markdown报告
report = comparison_tool.generate_report(results)
print(report)
```

## 实验脚本

### RQ1: 检测准确性

```bash
python experiments/rq1_accuracy.py
```

评估Pipeline-aware方法的检测准确性，输出：
- 总体Precision、Recall、F1-score
- 每个Smell类型的性能
- 详细的匹配结果

### RQ2: 检测能力对比

```bash
python experiments/rq2_coverage.py
```

对比多个方法的检测能力，输出：
- 各方法的性能排名
- Pipeline-aware独有的Smell类型
- 覆盖能力矩阵
- 统计显著性检验结果

## Ground Truth构建

### 交互式标注

```bash
python tools/build_ground_truth.py
# 选择 "1. 交互式标注"
```

### CSV批量导入

创建 `annotations.csv`:
```csv
file_path,smell_type,line_number,description,affected_nodes
pipeline_001.py,DATA_LEAKAGE,15,在划分前标准化,node_1,node_2
pipeline_001.py,MISSING_RANDOM_SEED,20,未设置random_state,node_3
```

然后运行:
```bash
python tools/build_ground_truth.py
# 选择 "2. 从CSV批量导入"
```

### 标注一致性检验

```python
from src.evaluation import calculate_cohen_kappa

annotator1 = ['DATA_LEAKAGE', 'MISSING_SEED', 'EXCESSIVE_COPY', ...]
annotator2 = ['DATA_LEAKAGE', 'MISSING_SEED', 'EXCESSIVE_COPY', ...]

kappa = calculate_cohen_kappa(annotator1, annotator2)
print(f"Cohen's Kappa: {kappa:.4f}")

if kappa > 0.7:
    print("标注一致性良好")
elif kappa > 0.4:
    print("标注一致性中等，需要讨论")
else:
    print("标注一致性较差，需要重新标注")
```

## 输出格式

### 评估结果JSON

```json
{
  "method_name": "Pipeline-aware",
  "overall_metrics": {
    "precision": 0.8750,
    "recall": 0.8235,
    "f1_score": 0.8485,
    "total_predictions": 120,
    "total_ground_truth": 136,
    "true_positives": 112,
    "false_positives": 8,
    "false_negatives": 24
  },
  "per_smell_metrics": {
    "DATA_LEAKAGE": {
      "precision": 0.9500,
      "recall": 0.9048,
      "f1_score": 0.9268
    },
    ...
  },
  "runtime_ms": 1234.56
}
```

### 方法比较JSON

```json
{
  "methods": [
    {
      "name": "Pipeline-aware",
      "precision": 0.8750,
      "recall": 0.8235,
      "f1_score": 0.8485,
      "runtime_ms": 1234.56
    },
    {
      "name": "Baseline-Keyword",
      "precision": 0.6500,
      "recall": 0.7000,
      "f1_score": 0.6739,
      "runtime_ms": 234.56
    }
  ],
  "best_method": "Pipeline-aware",
  "best_f1": 0.8485
}
```

### 统计检验报告

```markdown
# Statistical Comparison Report

## Descriptive Statistics

| Method | Mean | Median | Std | 95% CI |
|--------|------|--------|-----|--------|
| Pipeline-aware | 0.8485 | 0.8500 | 0.0234 | [0.8234, 0.8736] |
| Baseline-Keyword | 0.6739 | 0.6750 | 0.0345 | [0.6423, 0.7055] |

## Pairwise Comparisons

### Pipeline-aware_vs_Baseline-Keyword

**Paired t-test:**
- p-value: 0.0001
- Significant: Yes
- Better method: method1

**Effect Size:**
- Cohen's d: 1.2345
- Interpretation: large
```

## 性能优化建议

1. **批量处理**: 使用`evaluate_batch`而非多次调用`evaluate`
2. **并行计算**: 对独立文件的评估可以并行化
3. **缓存结果**: 保存中间结果避免重复计算
4. **增量评估**: 只评估变更的文件

## 常见问题

### Q: 如何选择匹配策略？

A: 
- 精确匹配（EXACT）：用于高质量的Ground Truth
- 行范围匹配（LINE_RANGE）：推荐用于大多数场景，容忍度设为2-3行
- 语义匹配（SEMANTIC）：用于跨行的复杂Smell

### Q: 如何处理不平衡的数据集？

A: 
- 使用F1-score而非Accuracy
- 报告每个Smell类型的性能
- 考虑使用加权平均

### Q: 如何确保统计检验的有效性？

A:
- 样本量至少30个
- 检查数据分布（正态性）
- 使用非参数检验（Wilcoxon）作为补充
- 报告效应量

## 扩展功能

### 自定义匹配策略

```python
class CustomMatcher(GroundTruthMatcher):
    def _custom_match(self, predictions, ground_truth):
        # 实现自定义匹配逻辑
        pass
```

### 自定义评估指标

```python
def custom_metric(predictions, ground_truth):
    # 实现自定义指标
    return score
```

## 参考文献

1. Powers, D. M. (2011). Evaluation: from precision, recall and F-measure to ROC, informedness, markedness and correlation.
2. Cohen, J. (1960). A coefficient of agreement for nominal scales.
3. Wilcoxon, F. (1945). Individual comparisons by ranking methods.

## 更新日志

- 2024-03-18: 初始版本发布
  - 实现三种匹配策略
  - 支持标准评估指标
  - 集成统计显著性检验
  - 提供完整的实验脚本
