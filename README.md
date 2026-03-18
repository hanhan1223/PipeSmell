# Pipeline-aware Smell Detection System

> 传统代码异味检测工具无法有效识别数据准备流程中的结构性问题。本研究提出一种Pipeline级别的代码异味检测方法，能够识别传统工具无法检测的workflow-level问题。

## 📚 研究概述

### 研究目标
提出一种 **Pipeline-aware Smell Detection** 方法，用于检测数据准备流程中的结构性问题（pipeline smell），并验证其在准确性、覆盖能力和实际工程价值上的优越性。

### 核心创新点
- **传统方法**：code-level smell detection
- **本研究**：pipeline-level structure-aware smell detection

### 研究问题
- **RQ1**: 检测准确性 - How accurately can the proposed approach detect pipeline smells?
- **RQ2**: 对比现有方法 - Can the proposed method detect pipeline-level smells that existing tools fail to detect?

## 🏗️ 系统架构

```
Code Parser (AST) 
       ↓
Pipeline Extractor
       ↓
Module Classifier
       ↓
Smell Detector
       ↓
Report Generator
```

### 核心组件
1. **Code Parser** - Python AST解析、关键API识别、控制流分析
2. **Pipeline Extractor** - Pipeline节点抽象、图构建、序列提取（核心创新）
3. **Module Classifier** - 5大模块划分（数据获取/清洗/特征/模型/辅助）
4. **Smell Detector** - 18种Pipeline Smell检测器
5. **Report Generator** - 文本/JSON/可视化报告

## 📦 安装

### 环境要求
- Python 3.8+
- pip

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/hanhan1223/PipeSmell.git
cd ccf-a-pipeline-smell-detection

# 安装依赖
pip install -r requirements.txt
```

### 依赖包

```text
networkx>=2.8      # Pipeline图结构
pandas>=1.5         # 数据处理
numpy>=1.23         # 数值计算
scikit-learn>=1.2    # 机器学习API
matplotlib>=3.6      # 可视化
seaborn>=0.12       # 统计图表
gitpython>=3.1       # GitHub数据收集
scipy>=1.10         # 统计检验
click>=8.0           # 命令行接口
tqdm>=4.64          # 进度条
graphviz>=0.20       # 可视化图
pytest>=7.2          # 测试框架
```

## 🚀 使用方法

### 命令行工具

```bash
# 显示帮助
python src/cli.py --help

# 检测单个文件
python src/cli.py detect data/example.py

# 批量检测目录
python src/cli.py batch data/ --output reports/

# 列出所有支持的Smell类型
python src/cli.py list-smells
```

#### 检测单个文件

```bash
python src/cli.py detect path/to/pipeline.py \
  --format json \
  --output report.json \
  --categories ORDER,REDUNDANCY,MISSING \
  --severity HIGH
```

参数说明：
- `-f, --format`: 报告格式（text/json/visual）
- `-o, --output`: 输出文件路径
- `--categories`: 检测的Smell类别（逗号分隔）
- `--severity`: 最小严重性级别（CRITICAL/HIGH/MEDIUM/LOW）

#### 批量检测

```bash
python src/cli.py batch data/ \
  --recursive \
  --pattern "*.py" \
  --output reports/ \
  --format json
```

参数说明：
- `-r, --recursive`: 递归遍历子目录
- `--pattern`: 文件匹配模式（默认*.py）

### Python API

```python
from src.smells.detector import DetectorRegistry
from src.core.pipeline import PipelineExtractor
from src.core.reporter import create_reporter

# 1. 提取Pipeline
extractor = PipelineExtractor()
pipeline = extractor.extract_from_file("example.py")

# 2. 运行检测
registry = DetectorRegistry()
result = registry.detect_all(pipeline)

# 3. 生成报告
reporter = create_reporter('text')
reporter.generate(result, "report.md")

# 4. 查看结果
summary = result.get_summary()
print(f"检测到 {summary['total_smells']} 个Smell")
```

## 📊 Pipeline Smell分类体系

### 6大类，18种Pipeline Smell

#### 1. 顺序类 (ORDER)
- **Data Leakage** - 数据泄露：在train_test_split前使用全局统计信息
- **Missing Evaluation** - 缺少评估：缺少模型评估步骤
- **Module Order Violation** - 模块顺序违反：操作顺序不符合预期

#### 2. 冗余类 (REDUNDANCY)
- **Repeated Transform** - 重复转换：对同一列进行多次相同类型的转换
- **Excessive Copy** - 过度复制：不必要的数据复制
- **Redundant Operation** - 冗余操作：已完成操作前的反向操作

#### 3. 缺失类 (MISSING)
- **Missing Random Seed** - 缺少随机种子：train_test_split未设置random_state
- **Missing Validation** - 缺少验证：未划分验证集
- **Missing Data Profiling** - 缺少数据探索：无head/describe等操作

#### 4. 性能类 (PERFORMANCE)
- **Inefficient Aggregation** - 低效聚合：循环逐行聚合而非向量化操作
- **Unnecessary Materialization** - 不必要持久化：频繁的中间结果保存
- **Large DataFrame Operation** - 大数据集操作：对大DataFrame的全量遍历

#### 5. 结构类 (STRUCTURE)
- **Circular Dependency** - 循环依赖：模块间的循环依赖关系
- **Improper Module Cohesion** - 内聚性差：模块包含多种不同类型的操作
- **Pipeline Fragmentation** - 碎片化：包含大量短小的操作链

#### 6. 可复现性类 (REPRODUCIBILITY)
- **Hardcoded Parameters** - 硬编码参数：超参数直接写死
- **Lack of Version Control** - 缺少版本控制：无requirements.txt
- **Non-deterministic Order** - 非确定性：使用set/dict的无序迭代

## 📝 项目结构

```
ccf-a-pipeline-smell-detection/
├── src/
│   ├── core/              # 核心模块
│   │   ├── config.py      # 配置管理
│   │   ├── logger.py      # 日志系统
│   │   ├── parser.py      # AST解析器
│   │   ├── pipeline.py    # Pipeline抽象
│   │   ├── modules.py     # 模块分类器
│   │   └── reporter.py    # 报告生成器
│   ├── smells/            # Smell检测器
│   │   ├── taxonomy.py    # Smell分类体系（18种）
│   │   ├── detector.py    # 检测器基类和注册表
│   │   ├── order_detectors.py
│   │   ├── redundancy_detectors.py
│   │   ├── missing_detectors.py
│   │   ├── performance_detectors.py
│   │   ├── structure_detectors.py
│   │   └── reproducibility_detectors.py
│   ├── baseline/          # 基线方法
│   ├── evaluation/        # 评估框架
│   └── cli.py            # 命令行接口
├── data/
│   ├── raw/              # 原始GitHub数据
│   └── ground_truth/     # 人工标注数据
├── experiments/          # 实验脚本
│   ├── rq1_accuracy.py    # RQ1实验
│   ├── rq2_coverage.py    # RQ2实验
│   └── results/          # 实验结果
├── docs/                # 文档
├── tests/               # 测试
├── requirements.txt     # 依赖列表
├── pyproject.toml      # 项目配置
└── README.md           # 本文件
```

## 🔬 实验设计

### RQ1: 检测准确性
- **输入**: 人工标注的Ground Truth数据集（200-300个Pipeline）
- **方法**: Pipeline-aware Detection vs Baseline Methods
- **指标**: Precision, Recall, F1-score

### RQ2: 检测能力
- **对比**: 本方法 vs 传统工具（SonarQube, PMD, 关键词检测等）
- **指标**: Number of smell types detected

