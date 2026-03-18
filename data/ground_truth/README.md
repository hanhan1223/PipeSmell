# Ground Truth数据集

本目录用于存放Pipeline Smell的Ground Truth标注数据。

## 目录结构

```
ground_truth/
├── README.md              # 本文件
├── ground_truth.json      # 合并后的完整Ground Truth数据集
├── candidates/            # 候选Pipeline文件
│   ├── pipeline_001.py
│   ├── pipeline_002.py
│   └── ...
└── annotations/           # 单个文件的标注
    ├── pipeline_001_gt.json
    ├── pipeline_002_gt.json
    └── ...
```

## Ground Truth格式

### 单文件标注格式

```json
{
  "file_path": "path/to/pipeline.py",
  "annotator": "张三",
  "annotation_date": "2024-01-15",
  "smells": [
    {
      "id": "path/to/pipeline.py:10:DATA_LEAKAGE",
      "smell_type": "DATA_LEAKAGE",
      "file_path": "path/to/pipeline.py",
      "line_number": 10,
      "severity": "CRITICAL",
      "category": "ORDER",
      "description": "在train_test_split之前对整个数据集进行标准化",
      "affected_nodes": ["node_1", "node_2"]
    }
  ]
}
```

### 合并后的Ground Truth格式

```json
[
  {
    "id": "path/to/pipeline.py:10:DATA_LEAKAGE",
    "smell_type": "DATA_LEAKAGE",
    "file_path": "path/to/pipeline.py",
    "line_number": 10,
    "severity": "CRITICAL",
    "category": "ORDER",
    "description": "在train_test_split之前对整个数据集进行标准化",
    "affected_nodes": ["node_1", "node_2"]
  },
  ...
]
```

## 字段说明

- `id`: 唯一标识符，格式为 `{file_path}:{line_number}:{smell_type}`
- `smell_type`: Smell类型，必须是18种预定义类型之一
- `file_path`: 源文件路径
- `line_number`: Smell所在行号
- `severity`: 严重性级别 (CRITICAL, HIGH, MEDIUM, LOW)
- `category`: Smell类别 (ORDER, REDUNDANCY, MISSING, PERFORMANCE, STRUCTURE, REPRODUCIBILITY)
- `description`: 详细描述
- `affected_nodes`: 影响的Pipeline节点列表（可选）

## 标注指南

### 1. 数据收集

从GitHub收集真实的数据准备Pipeline代码：

```bash
# 使用GitHub API搜索
keywords: "pandas sklearn train_test_split"
language: Python
stars: >100
```

### 2. 候选筛选

筛选标准：
- 包含完整的数据准备流程
- 代码行数在50-500行之间
- 包含至少3个Pipeline操作
- 代码质量参差不齐（既有好的也有坏的）

### 3. 标注流程

#### 方法1：使用交互式工具

```bash
python tools/build_ground_truth.py
# 选择 "1. 交互式标注"
```

#### 方法2：使用CSV批量导入

创建CSV文件 `annotations.csv`:

```csv
file_path,smell_type,line_number,description,affected_nodes
pipeline_001.py,DATA_LEAKAGE,15,在划分前标准化,node_1,node_2
pipeline_001.py,MISSING_RANDOM_SEED,20,未设置random_state,node_3
pipeline_002.py,EXCESSIVE_COPY,30,不必要的copy操作,node_5
```

然后运行:

```bash
python tools/build_ground_truth.py
# 选择 "2. 从CSV批量导入"
```

### 4. 标注一致性

为保证标注质量，建议：

1. **多人标注**: 每个文件至少由2人独立标注
2. **一致性检验**: 计算Cohen's Kappa系数，要求 κ > 0.7
3. **讨论解决**: 对不一致的标注进行讨论并达成共识

### 5. 合并标注

```bash
python tools/build_ground_truth.py
# 选择 "3. 合并标注文件"
```

## 数据集统计

目标规模：
- 文件数量: 200-300个
- Smell实例: 1000-2000个
- 每个Smell类型: 至少50个实例

当前状态：
- [ ] 数据收集完成
- [ ] 标注完成
- [ ] 一致性检验完成
- [ ] 数据集发布

## 使用示例

### 加载Ground Truth

```python
from src.evaluation import GroundTruthLoader

# 加载单个文件
gt = GroundTruthLoader.load_from_json("ground_truth.json")

# 加载目录中的所有文件
gt_by_file = GroundTruthLoader.load_from_directory("annotations/")
```

### 评估检测结果

```python
from src.evaluation import Evaluator, EvaluationConfig

config = EvaluationConfig()
evaluator = Evaluator(config)

result = evaluator.evaluate(
    predictions=my_predictions,
    ground_truth=gt,
    method_name="My Method"
)

print(f"Precision: {result.overall_metrics.precision:.4f}")
print(f"Recall: {result.overall_metrics.recall:.4f}")
print(f"F1-score: {result.overall_metrics.f1_score:.4f}")
```

## 注意事项

1. **隐私保护**: 确保标注的代码不包含敏感信息
2. **许可证**: 遵守原始代码的开源许可证
3. **版本控制**: 使用Git跟踪标注的变更
4. **备份**: 定期备份标注数据

## 联系方式

如有问题，请联系项目维护者。
