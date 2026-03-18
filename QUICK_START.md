# 快速启动指南

## 🚀 立即开始使用

### 1. 验证系统状态

```bash
# 运行测试确保一切正常
python tests/test_bug_fixes.py

# 预期输出: 7 passed
```

### 2. 测试检测功能

```bash
# 检测示例文件
python src/cli.py detect example_pipeline.py --format text

# 预期输出: 检测到多个Smell
```

### 3. 查看Smell目录

```bash
# 列出所有支持的Smell类型
python src/cli.py list-smells
```

## 📊 运行评估实验

### 准备Ground Truth数据

#### 方法1: 使用交互式工具
```bash
python tools/build_ground_truth.py
# 选择 "1. 交互式标注"
```

#### 方法2: 从CSV导入
```bash
# 1. 创建 annotations.csv
cat > annotations.csv << EOF
file_path,smell_type,line_number,description,affected_nodes
example_pipeline.py,DATA_LEAKAGE,15,在划分前标准化,node_1,node_2
example_pipeline.py,MISSING_RANDOM_SEED,20,未设置random_state,node_3
EOF

# 2. 运行导入
python tools/build_ground_truth.py
# 选择 "2. 从CSV批量导入"
```

### 运行RQ1实验

```bash
# 确保Ground Truth文件存在
# data/ground_truth/ground_truth.json

python experiments/rq1_accuracy.py

# 查看结果
cat experiments/results/rq1/rq1_summary.json
```

### 运行RQ2实验

```bash
python experiments/rq2_coverage.py

# 查看方法比较
cat experiments/results/rq2/method_comparison.json

# 查看统计检验
cat experiments/results/rq2/statistical_report.md
```

## 🔧 常用命令

### 检测单个文件
```bash
python src/cli.py detect path/to/pipeline.py \
  --format json \
  --output report.json \
  --severity HIGH
```

### 批量检测
```bash
python src/cli.py batch data/ \
  --recursive \
  --output reports/ \
  --format json
```

### 只检测特定类别
```bash
python src/cli.py detect pipeline.py \
  --categories ORDER,MISSING \
  --format text
```

## 📝 Python API使用

### 基础检测
```python
from src.smells.detector import DetectorRegistry
from src.core.pipeline import PipelineExtractor

# 1. 提取Pipeline
extractor = PipelineExtractor()
pipeline = extractor.extract_from_file("example.py")

# 2. 运行检测
registry = DetectorRegistry()
result = registry.detect_all(pipeline)

# 3. 查看结果
for smell in result.detected_smells:
    print(f"{smell.smell_type} at line {smell.location.line_number}")
```

### 评估检测结果
```python
from src.evaluation import (
    Evaluator,
    EvaluationConfig,
    MatchStrategy,
    GroundTruthLoader
)

# 1. 配置评估
config = EvaluationConfig(
    match_strategy=MatchStrategy.LINE_RANGE,
    line_tolerance=2
)

# 2. 加载Ground Truth
gt = GroundTruthLoader.load_from_json("ground_truth.json")

# 3. 评估
evaluator = Evaluator(config)
result = evaluator.evaluate(
    predictions=my_predictions,
    ground_truth=gt,
    method_name="My Method"
)

# 4. 查看指标
print(f"Precision: {result.overall_metrics.precision:.4f}")
print(f"Recall: {result.overall_metrics.recall:.4f}")
print(f"F1-score: {result.overall_metrics.f1_score:.4f}")
```

### 统计检验
```python
from src.evaluation import StatisticalTests

# 配对t检验
t_test = StatisticalTests.paired_t_test(
    method1_scores=[0.85, 0.87, 0.89],
    method2_scores=[0.78, 0.80, 0.82],
    alpha=0.05
)

print(f"p-value: {t_test['p_value']:.4f}")
print(f"显著性: {t_test['is_significant']}")

# 效应量
effect_size = StatisticalTests.cohen_d(
    method1_scores, method2_scores
)
print(f"Cohen's d: {effect_size:.4f}")
```

## 🎯 典型工作流程

### 场景1: 检测新的Pipeline文件

```bash
# 1. 检测
python src/cli.py detect new_pipeline.py --format json --output result.json

# 2. 查看结果
cat result.json | jq '.detected_smells[] | {type: .smell_type, line: .location.line_number}'

# 3. 生成报告
python src/cli.py detect new_pipeline.py --format text --output report.md
```

### 场景2: 评估新方法

```python
# 1. 运行你的方法
my_predictions = run_my_method(file_paths)

# 2. 加载Ground Truth
from src.evaluation import GroundTruthLoader
gt = GroundTruthLoader.load_from_json("ground_truth.json")

# 3. 评估
from src.evaluation import Evaluator, EvaluationConfig
evaluator = Evaluator(EvaluationConfig())
result = evaluator.evaluate(my_predictions, gt, "My Method")

# 4. 查看结果
print(result.get_summary())
```

### 场景3: 对比多个方法

```python
from src.evaluation import Evaluator, EvaluationConfig

evaluator = Evaluator(EvaluationConfig())
results = []

# 评估多个方法
for method_name, predictions in all_methods.items():
    result = evaluator.evaluate(predictions, gt, method_name)
    results.append(result)

# 生成比较报告
comparison = evaluator.compare_methods(results)

# 查看排名
for i, method in enumerate(comparison['methods'], 1):
    print(f"{i}. {method['name']}: F1={method['f1_score']:.4f}")
```

## 📚 更多资源

### 文档
- `README.md` - 项目概述
- `docs/EVALUATION_FRAMEWORK.md` - 评估框架详细文档
- `data/ground_truth/README.md` - Ground Truth数据集说明
- `BUG_FIXES_AND_IMPROVEMENTS.md` - Bug修复总结
- `NEXT_STEPS.md` - 下一步工作指南

### 示例
- `example_pipeline.py` - 包含18种Smell的示例文件
- `tests/test_bug_fixes.py` - 测试用例参考

### 工具
- `src/cli.py` - 命令行工具
- `tools/build_ground_truth.py` - Ground Truth构建工具
- `experiments/rq1_accuracy.py` - RQ1实验脚本
- `experiments/rq2_coverage.py` - RQ2实验脚本

## ❓ 常见问题

### Q: 如何添加新的Smell检测器？

A: 
1. 在`src/smells/taxonomy.py`中定义新的Smell
2. 创建检测器类继承`SmellDetector`
3. 实现`detect()`方法
4. 在`DetectorRegistry`中注册

### Q: 如何自定义匹配策略？

A:
```python
from src.evaluation import GroundTruthMatcher, MatchStrategy

# 使用行范围匹配，容忍度为3行
matcher = GroundTruthMatcher(
    strategy=MatchStrategy.LINE_RANGE,
    line_tolerance=3
)
```

### Q: 如何处理大量文件？

A:
```bash
# 使用批量检测
python src/cli.py batch data/ --recursive --output reports/

# 或使用Python API并行处理
from multiprocessing import Pool

def detect_file(file_path):
    # 检测逻辑
    pass

with Pool(processes=4) as pool:
    results = pool.map(detect_file, file_paths)
```

### Q: Ground Truth数据格式是什么？

A: 参考 `data/ground_truth/README.md`，基本格式：
```json
[
  {
    "id": "file.py:10:DATA_LEAKAGE",
    "smell_type": "DATA_LEAKAGE",
    "file_path": "file.py",
    "line_number": 10,
    "severity": "CRITICAL",
    "category": "ORDER",
    "description": "...",
    "affected_nodes": ["node_1", "node_2"]
  }
]
```

## 🐛 遇到问题？

### 检查系统状态
```bash
# 运行测试
python tests/test_bug_fixes.py

# 查看日志
tail -f logs/*.log
```

### 常见错误

#### 错误: "Ground Truth文件不存在"
```bash
# 解决: 创建Ground Truth文件
python tools/build_ground_truth.py
```

#### 错误: "无法提取Pipeline"
```bash
# 解决: 检查文件语法
python -m py_compile your_file.py
```

#### 错误: "检测器未注册"
```bash
# 解决: 检查DetectorRegistry是否正确初始化
python -c "from src.smells.detector import DetectorRegistry; r = DetectorRegistry(); print(r.get_supported_smell_types())"
```

## 🎉 开始你的实验！

```bash
# 1. 验证系统
python tests/test_bug_fixes.py

# 2. 测试检测
python src/cli.py detect example_pipeline.py

# 3. 构建Ground Truth
python tools/build_ground_truth.py

# 4. 运行实验
python experiments/rq1_accuracy.py
python experiments/rq2_coverage.py

# 5. 查看结果
ls experiments/results/
```

祝实验顺利！🚀
