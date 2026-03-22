# External-style benchmark（真实风格子集）

本目录与主数据集 `dataset/*.py` 配合使用：**无中文教学注释、无 “包含 XXX Smell” 式文件头**，用于近似 **Kaggle / 脚本式** 代码上的行为（仍为本仓库原创示例代码，非爬取的第三方源码，避免许可证问题）。

## 与主 `dataset` 的关系

| 集合 | 作用 |
|------|------|
| `dataset/example_*.py` + `ground_truth.json` | 对照文献定义的可复现示范；部分检测器仍依赖文件头 **marker**（与 README 对齐）。 |
| `dataset/external/*.py` + `ground_truth.json` | 弱化提示后的 **stress / 泛化抽查**；标注仅包含在本目录下**可稳定期望**的 smell（不强行覆盖依赖 marker 的类型）。 |

## 如何扩充为「真实第三方代码」

1. **选取**：优先 MIT/BSD/Apache 等允许研究复现的仓库，或获得授权的内部脱敏代码。  
2. **切片**：单文件或单 Notebook 导出的 `.py`，控制长度便于审阅。  
3. **标注**：复制本目录 `ground_truth.json` 中 `annotations` 结构；`file` 为相对本目录的文件名；`line_start`/`line_end` 与主 GT 一致。  
4. **一致性**：两人独立标再对齐，或同一标注者隔周重标，记录一致率。  
5. **评估**：在项目根执行：

```bash
python experiments/rq1_accuracy.py --gt dataset/external/ground_truth.json --output-dir experiments/results/rq1_external
```

## 当前文件说明（简要）

- `ext_*_style.py`：按文献常见反模式编写的 **英文注释/无 smell 标签** 脚本。  
- 干净样本 `ext_03_clean_style.py`：用于观察误报。  
- 详细逐条说明见各文件顶部 docstring（仅描述意图，不暴露 smell 类型名）。
