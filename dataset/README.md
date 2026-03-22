# Pipeline Smell Detection Dataset

## 数据集概述

这是一个专门为 **Pipeline Smell Detection System** 构建的标注数据集，包含 **40** 个 Python 机器学习 Pipeline 代码文件（`example_01`–`example_20` 与对应的变体 B `example_21`–`example_40`），涵盖全部 18 种 Pipeline Smell 类型。

## 文件结构

```
dataset/
├── example_01_data_leakage.py          # 数据泄露
├── example_02_missing_random_seed.py   # 缺少随机种子
├── example_03_missing_validation.py    # 缺少验证集
├── example_04_repeated_transform.py    # 重复转换
├── example_05_missing_evaluation.py    # 缺少评估
├── example_06_hardcoded_parameters.py  # 硬编码参数
├── example_07_nondeterministic_order.py # 非确定性顺序
├── example_08_inefficient_aggregation.py # 低效聚合
├── example_09_missing_data_profiling.py # 缺少数据探索
├── example_10_redundant_operation.py   # 冗余操作
├── example_11_excessive_copy.py        # 过度复制
├── example_12_module_order_violation.py # 模块顺序违反
├── example_13_circular_dependency.py   # 循环依赖
├── example_14_improper_module_cohesion.py # 模块内聚不当
├── example_15_pipeline_fragmentation.py # Pipeline碎片化
├── example_16_unnecessary_materialization.py # 不必要物化
├── example_17_large_dataframe_operation.py # 大DataFrame操作
├── example_18_lack_version_control.py  # 缺少版本控制
├── example_19_clean_pipeline.py        # 干净的Pipeline（无Smell）
├── example_20_multiple_smells.py       # 多种Smell混合
├── ground_truth.json                   # 标注文件
└── README.md                           # 本文件
```

## Smell类型分布

### 按类别统计

| 类别 | 数量 | Smell类型 |
|------|------|-----------|
| ORDER | 10 | DATA_LEAKAGE, MISSING_EVALUATION, MODULE_ORDER_VIOLATION |
| REDUNDANCY | 6 | REPEATED_TRANSFORM, EXCESSIVE_COPY, REDUNDANT_OPERATION |
| MISSING | 8 | MISSING_RANDOM_SEED, MISSING_VALIDATION, MISSING_DATA_PROFILING |
| PERFORMANCE | 6 | INEFFICIENT_AGGREGATION, UNNECESSARY_MATERIALIZATION, LARGE_DATA_FRAME_OPERATION |
| STRUCTURE | 6 | CIRCULAR_DEPENDENCY, IMPROPER_MODULE_COHESION, PIPELINE_FRAGMENTATION |
| REPRODUCIBILITY | 8 | HARDCODED_PARAMETERS, LACK_OF_VERSION_CONTROL, NON_DETERMINISTIC_ORDER |

### 按严重程度统计

| 严重程度 | 数量 |
|----------|------|
| CRITICAL | 6 |
| HIGH | 10 |
| MEDIUM | 18 |
| LOW | 10 |

## 使用方法

### 0. 外部风格子集（可选）

无中文 smell 提示的英文脚本见 **`dataset/external/`**（含独立 `ground_truth.json`）。评估示例：

```bash
python experiments/rq1_accuracy.py --gt dataset/external/ground_truth.json --output-dir experiments/results/rq1_external
```

### 1. 与系统对比测试（RQ1 准确性实验）

```bash
# 在项目根目录执行：自动读取 dataset/ground_truth.json 并输出指标到 experiments/results/rq1/
python experiments/rq1_accuracy.py
```

可选参数：`--gt <path>`、`--output-dir <path>`。

也可先用 CLI 批量检测，再自行用 `src.evaluation` API 对比预测与 `ground_truth.json`。

### 2. 单独测试某个文件

```bash
python src/cli.py detect D:\PipeSmell\dataset\example_01_data_leakage.py
```

### 3. 加载Ground Truth进行程序化分析

```python
import json

with open('D:\\PipeSmell\\dataset\\ground_truth.json', 'r', encoding='utf-8') as f:
    ground_truth = json.load(f)

# 获取所有标注
annotations = ground_truth['annotations']

# 获取统计信息
stats = ground_truth['statistics']
print(f"Total smells: {stats['total_smells']}")
```

## 标注格式

每个标注包含以下字段：

```json
{
  "file": "example_01_data_leakage.py",
  "smells": [
    {
      "type": "DATA_LEAKAGE",
      "line_start": 16,
      "line_end": 17,
      "description": "在train_test_split之前对整个数据集执行StandardScaler.fit()",
      "severity": "CRITICAL"
    }
  ]
}
```

## 注意事项

1. **文件19 / 39**（`example_19_clean_pipeline.py`、`example_39_clean_pipeline_b.py`）为**干净 Pipeline**，无 Smell，用于对比测试
2. **文件20 / 40**（`example_20_multiple_smells.py`、`example_40_multiple_smells_b.py`）为**多种 Smell 混合**，用于多标签检测
3. 所有代码都是**可运行的Python代码**，但可能需要安装依赖：`pip install pandas scikit-learn numpy matplotlib`

## 扩展数据集

如需扩展数据集，可以：

1. 复制现有文件作为模板
2. 修改代码添加新的Smell变体
3. 在 `ground_truth.json` 中添加相应标注
4. 更新统计信息

## 许可证

本数据集仅供研究和测试使用。
