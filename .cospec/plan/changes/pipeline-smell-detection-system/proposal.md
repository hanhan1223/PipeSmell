# 变更：构建 Pipeline-aware Smell Detection 检测系统

## 原因
传统代码异味检测工具无法有效识别数据准备流程（Data Preparation Pipeline）中的结构性问题，这些流程具有复杂的顺序依赖和模块特征，且其质量问题（如数据泄露、重复转换、性能问题）直接影响到机器学习模型的可靠性和性能。本研究需要构建一个基于Python的语义分析系统，能够从Pipeline级别检测15-20种结构性代码异味，并通过实验验证其在准确性和覆盖能力上优于传统方法。

## 变更内容
- **系统架构**：Code Parser (AST) → Pipeline Extractor → Module Classifier → Smell Detector → Report Generator
- **核心技术**：基于Python AST、类型推断和数据流分析的Pipeline抽象与模块划分
- **Smell分类**：设计并实现15-20种Pipeline级别的代码异味检测规则
  - 顺序类：data leakage, missing evaluation, module order violation
  - 冗余类：repeated transform, excessive copy, redundant operation
  - 缺失类：missing random seed, missing validation, missing data profiling
  - 性能类：inefficient aggregation, unnecessary materialization
  - 结构类：circular dependency, improper module cohesion
  - 可复现类：lack of version control, hard-coded parameters
  - 等等...
- **模块划分**：数据获取模块、数据清洗模块、特征处理模块、模型操作模块、辅助逻辑模块
- **实验验证**：实现RQ1（准确性）和RQ2（检测能力）的评估框架

## 影响
- **受影响的规范**：Pipeline Smell Taxonomy
- **受影响的代码**：
    - `src/core/`: 系统核心架构（Parser、Extractor、Classifier、Detector）
    - `src/analysis/`: 语义分析引擎（类型推断、数据流分析）
    - `src/smells/`: 15-20种Smell检测器实现
    - `src/baseline/`: 基线方法实现（SonarQube、PMD、关键词检测、启发式规则）
    - `src/evaluation/`: 评估框架（Precision、Recall、F1计算）
    - `data/ground_truth/`: 人工标注数据集存储
    - `experiments/`: 实验脚本和结果分析

## 核心创新
1. **Pipeline抽象**：将代码转换为Pipeline图结构，提取操作序列和依赖关系
2. **模块感知**：基于语义功能进行模块划分，分析模块间的顺序约束
3. **流程感知**：检测跨模块的结构性问题，而非局部的代码模式
4. **语义分析**：结合类型推断和数据流分析，提高检测准确性

## 预期成果
- 完整的Pipeline-aware Smell Detection系统（Python实现）
- 15-20种Pipeline Smell的形式化定义和检测规则
  - 完整的Pipeline提取和模块分类算法
- Ground Truth标注数据集（200-300个Pipeline）
- 实验结果报告（RQ1/RQ2的Precision/Recall/F1对比）
- 可复现的实验脚本和数据分析代码
