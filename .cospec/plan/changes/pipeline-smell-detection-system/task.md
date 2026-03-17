## 实施

### Phase 1: 项目初始化和基础架构
- [x] 1.1 创建项目目录结构
     【目标对象】`src/core/`, `src/analysis/`, `src/smells/`, `src/baseline/`, `src/evaluation/`, `data/ground_truth/`, `data/raw/`, `experiments/`, `docs/`, `tests/`, `tools/`
     【修改目的】建立标准化的项目目录布局
     【修改方式】创建目录层级
     【相关依赖】无
     【修改内容】
        - 创建 `src/core/` 用于核心架构模块（parser、pipeline、modules、reporter）
        - 创建 `src/analysis/` 用于语义分析引擎（type_inference、dataflow）
        - 创建 `src/smells/` 用于15-20种Smell检测器（taxonomy、detector、各分类检测器）
        - 创建 `src/baseline/` 用于基线方法实现（keyword、heuristic、sonarqube_adapter、pmd_adapter）
        - 创建 `src/evaluation/` 用于评估框架（metrics、evaluation、statistics）
        - 创建 `data/ground_truth/` 用于标注数据（candidates/、gold_standard.json）
        - 创建 `data/raw/` 用于原始GitHub数据（repos/）
        - 创建 `experiments/` 用于实验脚本（rq1_accuracy.py、rq2_coverage.py、analysis.py、results/、figures/、report/）
        - 创建 `docs/` 用于文档（api_reference.md、experiments.md、smell_catalog.md）
        - 创建 `tests/` 用于测试（unit/、integration/）
        - 创建 `tools/` 用于工具脚本（annotation_tool.py、github_collector.py、pipeline_extractor.py）

- [x] 1.2 配置Python项目依赖和开发环境
     【目标对象】`requirements.txt`, `pyproject.toml`, `.gitignore`
     【修改目的】定义项目依赖和开发工具配置
     【修改方式】编写配置文件内容
     【相关依赖】无
     【修改内容】
        - 创建 `requirements.txt`，声明版本固定的依赖包：networkx>=2.8, pandas>=1.5, numpy>=1.23, scikit-learn>=1.2, matplotlib>=3.6, seaborn>=0.12, gitpython>=3.1, scipy>=1.10, typing-extensions, dataclasses, click>=8.0, tqdm>=4.64, graphviz>=0.20, pytest>=7.2
        - 创建 `pyproject.toml`，在[project]部分定义name="pipeline-smell-detection"、version="0.1.0"、dependencies，在[build-system]部分指定requires=["setuptools>=61.0"]、build-backend="setuptools.build_meta"
        - 创建 `.gitignore`，排除：__pycache__/, *.py[cod], .pytest_cache/, .coverage, htmlcov/, data/raw/repos/, experiments/results/, experiments/figures/, .DS_Store, *.egg-info/

- [x] 1.3 实现配置管理和日志系统
     【目标对象】`src/core/config.py::ConfigManager类`, `src/core/logger.py::Logger类`
     【修改目的】提供统一的配置加载和日志记录功能
     【修改方式】使用Python标准库logging、json、pathlib构建类
     【相关依赖】Python标准库logging、json、pathlib
     【修改内容】
        - 在 `src/core/config.py` 中定义 `ConfigManager` 类：实现load(config_path: str)方法从JSON配置文件读取字典数据，实现get(key: str, default=None)方法取值，实现get_bool/set_int/set_float等类型安全的方法，实现reload()方法重新加载配置
        - 在 `src/core/logger.py` 中定义 `Logger` 类：实现setup(name: str, log_file: str, level: str)方法配置logger对象，使用RotatingFileHandler(maxBytes=10MB, backupCount=5)实现日志滚动，同时添加StreamHandler输出到控制台，定义format格式为'%(asctime)s - %(name)s - %(levelname)s - %(message)s'，实现debug/info/warning/error/critical便捷方法

### Phase 2: 代码解析器 (Code Parser) 实现
- [x] 2.1 实现AST解析器基础框架
     【目标对象】`src/core/parser.py::ASTParser类`
     【修改目的】解析Python代码为AST，提取语法结构信息
     【修改方式】定义ASTParser类，封装Python标准库ast模块
     【相关依赖】`src/core/logger.py`
     【修改内容】
        - 定义 `ASTParser` 类，在__init__中初始化logger对象
        - 实现 `parse_file(file_path: str) -> ast.Module` 方法：使用open(file_path, encoding='utf-8')读取文件，调用ast.parse(code, filename=file_path)，捕获SyntaxError和UnicodeDecodeError并记录error日志后返回None
        - 实现 `parse_code(code: str) -> ast.Module` 方法：直接调用ast.parse(code)
        - 实现 `extract_imports(node: ast.Module) -> List[ImportNode]` 方法：遍历node.body，识别ast.Import和ast.ImportFrom节点，提取module名和import列表
        - 实现 `extract_functions(node: ast.Module) -> List[FunctionNode]` 方法：识别ast.FunctionDef和ast.AsyncFunctionDef节点，提取函数名、参数列表、返回类型
        - 实现 `extract_classes(node: ast.Module) -> List[ClassNode]` 方法：识别ast.ClassDef节点，提取类名、基类列表、方法列表

- [x] 2.2 实现关键API识别和调用提取
     【目标对象】`src/core/parser.py::APIExtractor类`
     【修改目的】识别数据准备流程中的关键API调用（read_csv, fillna, StandardScaler等）
     【修改方式】定义APIExtractor类，遍历AST(Call)节点进行模式匹配
     【相关依赖】`src/core/parser.py`::ASTParser
     【修改内容】
        - 在模块级别定义 `KEY_APIS` 常量：字典结构为{'pandas': ['read_csv', 'fillna', 'dropna', 'drop_duplicates', 'merge', 'groupby'], 'sklearn.preprocessing': ['StandardScaler', 'MinMaxScaler'], 'sklearn.model_selection': ['train_test_split'], 'sklearn': ['fit', 'transform', 'predict', 'score']}
        - 定义 `APIExtractor` 类：在__init__中接收key_aps字典初始化
        - 实现 `extract_calls(node: ast.Module) -> List[APICall]` 方法：使用ast.walk(node)遍历所有节点，筛选ast.Call类型节点
        - 实现 `match_api(call_node: ast.Call) -> APICall` 方法：判断是否为属性调用（ast.Attribute），递归解析调用链（如df.fillna().value_counts()），提取函数名和所属库，匹配KEY_APIS字典
        - 实现 `extract_args(call_node: ast.Call) -> Dict[str, ArgInfo]` 方法：遍历call_node.args（位置参数）和call_node.keywords（关键字参数），识别变量名（ast.Name）和常量值
        - 实现 `track_return_variable(node: ast.Call) -> Optional[str]` 方法：检查父节点是否为ast.Assign类型，提取target.id作为返回值变量名

- [x] 2.3 实现控制流和数据依赖分析
     【目标对象】`src/core/parser.py::ControlFlowAnalyzer类`
     【修改目的】提取代码中的控制流（if/for/while）和数据依赖关系
     【修改方式】定义ControlFlowAnalyzer类，分析AST控制流节点
     【相关依赖】`src/core/parser.py`::APIExtractor
     【修改内容】
        - 定义 `ControlFlowAnalyzer` 类：在__init__中初始化空字典存储变量定义-映射关系
        - 实现 `analyze_control_flow(node: ast.Module) -> Dict[str, Any]` 方法：遍历node.body，识别ast.If节点保存条件和分支，识别ast.For/ast.While节点保存循环变量和循环体
        - 实现 `track_variable_usage(node: ast.Module) -> Dict[str, List[UsageInfo]]` 方法：使用ast.walk(node)查找所有ast.Name节点，检查ctx类型：ast.Store为定义点、ast.Load为使用点，按变量名分组存储使用信息
        - 实现 `analyze_loops(node: ast.Module) -> List[LoopInfo]` 方法：提取ast.For节点获取iter变量和循环体，提取ast.While节点获取测试条件和循环体
        - 实现 `analyze_conditionals(node: ast.Module) -> List[ConditionalInfo]` 方法：提取ast.If节点的test表达式、body（true分支）、orelse（false分支）
        - 实现 `build_dependency_graph(api_calls: List[APICall], var_usage: Dict) -> Dict[str, Set[str]]` 方法：遍历api_calls，对每个API调用检查其输入变量是否为其他API调用的输出变量，建立变量到变量的依赖关系，构建依赖图字典{var_name: [dependent_vars]}

### Phase 3: Pipeline Extractor 实现（核心创新）
- [x] 3.1 实现Pipeline操作节点抽象
     【目标对象】`src/core/pipeline.py::PipelineNode类`, `src/core/pipeline.py::OperationType枚举`
     【修改目的】将代码操作抽象为Pipeline节点，包含操作类型、输入、输出
     【修改方式】定义PipelineNode数据类和OperationType枚举
     【相关依赖】`src/core/parser.py`::APIExtractor
     【修改内容】
        - 使用Python的@dataclass装饰器定义 `PipelineNode` 类：字段包括node_id(str)唯一标识、operation_type(OperationType枚举)、api_name(str)、inputs(List[str])输入变量列表、outputs(List[str])输出变量列表、line_number(int)代码行号、code_snippet(str)代码片段、location(str)文件路径、attributes(Dict[str, Any])扩展属性字典
        - 定义 `OperationType` 枚举类：成员包括DATA_LOADING、DATA_CLEANING、FEATURE_ENGINEERING、MODEL_OPERATION、VALIDATION、TRAIN_TEST_SPLIT、AUXILIARY、OTHER
        - 实现 `from_api_call(api_call: APICall, node_id: int) -> PipelineNode` 类方法：根据api_call的函数调用名称匹配operation_type（如read_csv匹配DATA_LOADING），抽取api_call的变量名列表作为inputs，抽取返回值变量名作为outputs
        - 实现 `to_dict(self) -> Dict` 方法：将PipelineNode序列化为json.dumps兼容的字典

- [x] 3.2 实现Pipeline图构建算法
     【目标对象】`src/core/pipeline.py::PipelineGraph类`
     【修改目的】将操作节点连接成Pipeline图，表示操作顺序
     【修改方式】定义PipelineGraph类，使用networkx.DiGraph表示有向图
     【相关依赖】`src/core/parser.py`::ControlFlowAnalyzer、networkx>=2.8
     【修改内容】
        - 定义 `PipelineGraph` 类：在__init__中初始化self.graph = networkx.DiGraph()作为内部存储
        - 实现 `add_node(self, node: PipelineNode)` 方法：将PipelineNode添加到图中，使用node.node_id作为节点标识，其他属性存储为节点属性
        - 实现 `add_edge(self, source_id: str, target_id: str, edge_type: str)` 方法：在两个节点间添加有向边，edge_type为'data_flow'、'control_flow'或'backward'
        - 实现 `build_from_dependencies(self, nodes: List[PipelineNode], dep_graph: Dict)` 方法：遍历nodes列表，对每个节点的inputs变量检查是否在其他节点的outputs中，若匹配则添加'data_flow'边
        - 实现 `handle_branches_and_loops(self, cf_info: Dict)` 方法：处理循环节点添加'backward'边，处理条件分支添加'control_flow'边
        - 实现 `topological_sort(self) -> List[str]` 方法：使用networkx.topological_sort(self.graph)返回节点ID排序，捕获NetworkXError处理循环依赖
        - 实现 `get_execution_paths(self) -> List[List[str]]` 方法：使用networkx.all_simple_paths()提取所有可能的执行路径

- [x] 3.3 实现Pipeline序列提取
     【目标对象】`src/core/pipeline.py::PipelineSequenceExtractor类`
     【修改目的】从Pipeline图中提取线性的操作序列，用于后续分析
     【修改方式】定义PipelineSequenceExtractor类，实现图遍历算法
     【相关依赖】`src/core/pipeline.py`::PipelineGraph
     【修改内容】
        - 定义 `PipelineSequenceExtractor` 类：在__init__中接收PipelineGraph实例
        - 实现 `extract_linear_sequence(self) -> List[PipelineNode]` 方法：调用graph.topological_sort()获取排序后的节点ID列表，通过节点ID映射回PipelineNode对象
        - 实现 `identify_branch_points(self) -> List[str]` 方法：遍历graph中出度>1的节点，返回分支点节点ID列表
        - 实现 `identify_merge_points(self) -> List[str]` 方法：遍历graph中入度>1的节点，返回汇合点节点ID列表
        - 实现 `extract_main_path(self) -> List[PipelineNode]` 方法：基于节点operation_type推断主路径，从DATA_LOADING类型节点开始到MODEL_OPERATION类型节点结束，选择最长路径
        - 实现 `split_independent_pipelines(self) -> List[List[PipelineNode]]` 方法：使用networkx.weakly_connected_components()识别独立的Pipeline子图，返回多个Pipeline序列列表

### Phase 4: 模块分类器 (Module Classifier) 实现
- [x] 4.1 定义模块分类标准
     【目标对象】`src/core/modules.py::ModuleType枚举`, `src/core/modules.py::MODULE_DEFINITIONS常量`
     【修改目的】定义5大模块的语义特征和分类规则
     【修改方式】定义枚举和常量映射
     【相关依赖】无
     【修改内容】
        - 定义 `ModuleType` 枚举类：成员包括DATA_ACQUISITION（数据获取）、DATA_CLEANING（数据清洗）、FEATURE_ENGINEERING（特征工程）、MODEL_OPERATION（模型操作）、AUXILIARY_LOGIC（辅助逻辑）
        - 定义 `MODULE_DEFINITIONS` 字典常量：{ModuleType.DATA_ACQUISITION: ['read_csv', 'read_excel', 'load_data'], ModuleType.DATA_CLEANING: ['fillna', 'dropna', 'drop_duplicates', 'replace'], ModuleType.FEATURE_ENGINEERING: ['get_dummies', 'StandardScaler', 'MinMaxScaler', 'PCA'], ModuleType.MODEL_OPERATION: ['train_test_split', 'fit', 'predict', 'score', 'cross_val_score'], ModuleType.AUXILIARY_LOGIC: ['print', 'head', 'describe', 'info']}
        - 定义 `MODULE_ORDER_CONSTRAINTS` 列表常量：[ModuleType.DATA_ACQUISITION, ModuleType.DATA_CLEANING, ModuleType.FEATURE_ENGINEERING, ModuleType.MODEL_OPERATION]

- [x] 4.2 实现操作到模块的映射算法
     【目标对象】`src/core/modules.py::ModuleClassifier类`
     【修改目的】将每个Pipeline操作节点分类到对应模块
     【修改方式】定义ModuleClassifier类，基于operation_type和api_name进行分类
     【相关依赖】`src/core/pipeline.py`::PipelineNode、`src/core/modules.py`::MODULE_DEFINITIONS
     【修改内容】
        - 定义 `ModuleClassifier` 类：在__init__中初始化MODULE_DEFINITIONS映射
        - 实现 `classify_node(self, node: PipelineNode) -> ModuleType` 方法：遍历MODULE_DEFINITIONS字典，若node.api_name在某个ModuleType的操作列表中则返回该ModuleType，未匹配则返回AUXILIARY_LOGIC
        - 实现 `classify_pipeline(self, nodes: List[PipelineNode]) -> List[ModuleNode]` 方法：对每个PipelineNode应用classify_node()，生成ModuleNode列表（包含原有PipelineNode信息和module_type字段）
        - 实现 `get_module_sequence(self, module_nodes: List[ModuleNode]) -> List[ModuleType]` 方法：提取ModuleNode列表中的module_type，返回模块类型序列

- [x] 4.3 实现模块边界识别和验证
     【目标对象】`src/core/modules.py::ModuleBoundaryDetector类`
     【修改目的】识别模块间的边界，检查模块划分的合理性
     【修改方式】定义ModuleBoundaryDetector类，分析模块序列
     【相关依赖】`src/core/modules.py`::ModuleClassifier、`src/core/modules.py`::MODULE_ORDER_CONSTRAINTS
     【修改内容】
        - 定义 `ModuleBoundaryDetector` 类：在__init__中初始化MODULE_ORDER_CONSTRAINTS
        - 实现 `detect_transitions(self, module_sequence: List[ModuleType]) -> List[ModuleTransition]` 方法：遍历module_sequence，识别相邻不同ModuleType的位置，记录transition_from、transition_to、index
        - 实现 `validate_order(self, module_sequence: List[ModuleType]) -> ValidationResult` 方法：检查模块序列是否符合MODULE_ORDER_CONSTRAINTS定义的顺序约束，检测是否存在违反预期的模块转换（如MODEL_OPERATION后出现DATA_ACQUISITION）
        - 实现 `identify_violations(self, module_sequence: List[ModuleType]) -> List[OrderViolation]` 方法：返回所有违反顺序约束的模块转换，包括位置、当前模块类型、期望的模块类型

### Phase 5: Smell分类体系定义
- [x] 5.1 定义完整Smell分类体系（15-20种）
     【目标对象】`src/smells/taxonomy.py::PipelineSmell基类`, `src/smells/taxonomy.py::具体Smell类`
     【修改目的】形式化定义15-20种Pipeline级别的代码异味
     【修改方式】定义PipelineSmell基类和具体Smell数据类
     【相关依赖】无
     【修改内容】
        - 使用@dataclass定义 `PipelineSmell` 基类：字段包括name(str)Smell名称、category(str)类别、description(str)描述、severity(str)严重性、detection_pattern(str)检测模式
        - 定义 `SmellCategory` 枚举：包括ORDER、REDUNDANCY、MISSING、PERFORMANCE、STRUCTURE、REPRODUCIBILITY
        - 定义 `SeverityLevel` 枚举：包括CRITICAL、HIGH、MEDIUM、LOW
        - 定义15-20种具体Smell常量对象（作为PipelineSmell类的实例）：
          * 顺序类：DATA_LEAKAGE（在train_test_split前使用全局统计）、MISSING_EVALUATION（缺少模型评估）、MODULE_ORDER_VIOLATION（模块顺序违反预期）
          * 冗余类：REPEATED_TRANSFORM（重复数据转换）、EXCESSIVE_COPY（不必要数据复制）、REDUNDANT_OPERATION（冗余操作如dropna后fillna）
          * 缺失类：MISSING_RANDOM_SEED（缺少随机种子）、MISSING_VALIDATION（缺少验证集）、MISSING_DATA_PROFILING（缺少数据探索）
          * 性能类：INEFFICIENT_AGGREGATION（低效聚合）、UNNECESSARY_MATERIALIZATION（不必要中间结果持久化）、LARGE_DATAFRAME_OPERATION（大DataFrame低效操作）
          * 结构类：CIRCULAR_DEPENDENCY（循环依赖）、IMPROPER_MODULE_COHESION（模块内聚性差）、PIPELINE_FRAGMENTATION（Pipeline过于碎片化）
          * 可复现类：HARDCODED_PARAMETERS（硬编码参数）、LACK_OF_VERSION_CONTROL（缺少版本控制）、NON_DETERMINISTIC_ORDER（非确定性顺序）

- [x] 5.2 实现Smell形式化描述
     【目标对象】`src/smells/taxonomy.py::get_detection_pattern()方法`
     【修改目的】为每个Smell提供形式化的检测模式描述
     【修改方式】描述检测逻辑的抽象模式
     【相关依赖】`src/smells/taxonomy.py`::PipelineSmell
     【修改内容】
        - 在每个具体Smell对象的detection_pattern字段中描述检测模式：例如DATA_LEAKAGE的detection_pattern为"存在StandardScaler.fit()操作位于train_test_split()之前"
        - 为每个Smell定义具体的检测条件集合：例如MISSING_RANDOM_SEED的检测条件"train_test_split、shuffle、split函数未设置random_state参数"
        - 定义Smell之间的层级关系：如果检测到某个高层Smell，可能关联多个低层Smell

### Phase 6: 15-20种Smell检测器实现
- [x] 6.1 实现Smell检测器基础框架
     【目标对象】`src/smells/detector.py::SmellDetector基类`, `src/smells/detector.py::数据类`
     【修改目的】提供统一的检测器接口和检测结果数据结构
     【修改方式】定义基类和数据类
     【相关依赖】`src/smells/taxonomy.py`::PipelineSmell
     【修改内容】
        - 使用@dataclass定义 `SmellInstance` 类：字段包括smell_type(str)Smell类型、location(LocationInfo)位置信息（file_path, line_number, column, code_snippet）、description(str)详细描述、severity(str)严重性、affected_nodes(List[str])影响的Pipeline节点ID列表、suggestion(str)修复建议
        - 使用@dataclass定义 `DetectionResult` 类：字段包括pipeline_id(str)Pipeline标识、file_path(str)文件路径、total_operations(int)总操作数、detected_smells(List[SmellInstance])检测到的Smell列表、statistics(Dict)统计信息（各类别Smell数量）
        - 定义 `SmellDetector` 抽象基类：定义抽象方法detect(self, pipeline_graph: PipelineGraph, module_sequence: List[ModuleType]) -> List[SmellInstance]，子类必须实现此方法，提供get_smell_type()方法返回检测器对应的Smell类型

- [x] 6.2 实现顺序类Smell检测器（3种）
     【目标对象】`src/smells/order_detectors.py::DataLeakageDetector类`, `src/smells/order_detectors.py::MissingEvaluationDetector类`, `src/smells/order_detectors.py::ModuleOrderViolationDetector类`
     【修改目的】检测Data Leakage, Missing Evaluation, Module Order Violation
     【修改方式】定义检测器类，分析模块序列和操作顺序
     【相关依赖】`src/smells/detector.py`::SmellDetector、`src/core/pipeline.py`::PipelineGraph、`src/core/modules.py`::ModuleClassifier
     【修改内容】
        - 定义 `DataLeakageDetector` 类继承SmellDetector：实现detect()方法遍历Pipeline nodes，查找StandardScaler.fit、MinMaxScaler.fit、SimpleImputer.fit等操作，检查这些操作的line_number是否小于train_test_split的line_number，若在之前则生成SmellInstance
        - 定义 `MissingEvaluationDetector` 类继承SmellDetector：实现detect()方法检查Pipeline末尾是否存在模型评估操作（predict、score、evaluate、cross_val_score），若无则生成SmellInstance
        - 定义 `ModuleOrderViolationDetector` 类继承SmellDetector：实现detect()方法接收module_sequence，调用ModuleBoundaryDetector.validate_order()，返回OrderViolation列表转换为SmellInstance

- [x] 6.3 实现冗余类Smell检测器（3种）
     【目标对象】`src/smells/redundancy_detectors.py::RepeatedTransformDetector类`, `src/smells/redundancy_detectors.py::ExcessiveCopyDetector类`, `src/smells/redundancy_detectors.py::RedundantOperationDetector类`
     【修改目的】检测Repeated Transform, Excessive Copy, Redundant Operation
     【修改方式】定义检测器类，分析重复操作和数据流
     【相关依赖】`src/smells/detector.py`::SmellDetector、`src/core/pipeline.py`::PipelineGraph
     【修改内容】
        - 定义 `RepeatedTransformDetector` 类继承SmellDetector：实现detect()方法按操作类型分组Pipeline nodes，识别对同一组变量（inputs匹配）执行多次相同转换的情况，生成SmellInstance记录重复位置
        - 定义 `ExcessiveCopyDetector` 类继承SmellDetector：实现detect()方法检查DataFrame.copy()调用，分析后续操作是否真正需要副本（若副本后无修改或原数据未被使用则标记为excessive），生成SmellInstance
        - 定义 `RedundantOperationDetector` 类继承SmellDetector：实现detect()方法查找冲突的操作序列（如dropna后对同一变量执行fillna），根据dataflow建立操作依赖，检测到已完成操作的逆向操作则生成SmellInstance

- [x] 6.4 实现缺失类Smell检测器（3种）
     【目标对象】`src/smells/missing_detectors.py::MissingRandomSeedDetector类`, `src/smells/missing_detectors.py::MissingValidationDetector类`, `src/smells/missing_detectors.py::MissingDataProfilingDetector类`
     【修改目的】检测Missing Random Seed, Missing Validation, Missing Data Profiling
     【修改方式】定义检测器类，检查关键操作的存在性
     【相关依赖】`src/smells/detector.py`::SmellDetector、`src/core/pipeline.py`::PipelineGraph
     【修改内容】
        - 定义 `MissingRandomSeedDetector` 类继承SmellDetector：实现detect()方法查找train_test_split、shuffle、split等API调用，检查其kwargs中是否包含'random_state'参数或检查是否有np.random.seed()、random.seed()全局设置，若缺失则生成SmellInstance
        - 定义 `MissingValidationDetector` 类继承SmellDetector：实现detect()方法检查是否存在train_test_split或KFold等验证集划分操作，若Pipeline中只有训练操作无验证则生成SmellInstance
        - 定义 `MissingDataProfilingDetector` 类继承SmellDetector：实现detect()方法检查是否存在数据探索操作（df.head、df.describe、df.info、df.shape等），若在数据加载后无任何探索操作则生成SmellInstance

- [x] 6.5 实现性能类Smell检测器（3种）
     【目标对象】`src/smells/performance_detectors.py::InefficientAggregationDetector类`, `src/smells/performance_detectors.py::UnnecessaryMaterializationDetector类`, `src/smells/performance_detectors.py::LargeDataFrameOperationDetector类`
     【修改目的】检测Inefficient Aggregation, Unnecessary Materialization, Large DataFrame Operation
     【修改方式】定义检测器类，分析操作复杂度和资源使用模式
     【相关依赖】`src/smells/detector.py`::SmellDetector、`src/core/pipeline.py`::PipelineGraph
     【修改内容】
        - 定义 `InefficientAggregationDetector` 类继承SmellDetector：实现detect()方法检查For循环体内对DataFrame进行逐行操作（如iterrows、逐行append），检测是否存在可向量化的替代操作（如groupby、agg），生成SmellInstance记录循环位置
        - 定义 `UnnecessaryMaterializationDetector` 类继承SmellDetector：实现detect()方法检查df.to_csv、df.to_parquet、df.to_pickle等持久化操作，分析后续代码是否重新加载同一数据，若中间结果仅用于传递而无外部读取需求则标记为不必要
        - 定义 `LargeDataFrameOperationDetector` 类继承SmellDetector：实现detect()方法检查对大DataFrame的全量遍历操作（如df.iteritems()、df[col].apply逐行），若无明确必要理由则生成SmellInstance

- [x] 6.6 实现结构类Smell检测器（3种）
     【目标对象】`src/smells/structure_detectors.py::CircularDependencyDetector类`, `src/smells/structure_detectors.py::ImproperModuleCohesionDetector类`, `src/smells/structure_detectors.py::PipelineFragmentationDetector类`
     【修改目的】检测Circular Dependency, Improper Module Cohesion, Pipeline Fragmentation
     【修改方式】定义检测器类，分析模块间关系和Pipeline结构
     【相关依赖】`src/smells/detector.py`::SmellDetector、`src/core/pipeline.py`::PipelineGraph、`src/core/modules.py`::ModuleClassifier
     【修改内容】
        - 定义 `CircularDependencyDetector` 类继承SmellDetector：实现detect()方法检查PipelineGraph是否存在循环，使用networkx.simple_cycles()检测，若发现环则生成SmellInstance列出环中的节点
        - 定义 `ImproperModuleCohesionDetector` 类继承SmellDetector：实现detect()方法按模块分组nodes，计算模块内操作类型的多样性（相似度），若同一模块包含多种语义无关的操作则生成SmellInstance
        - 定义 `PipelineFragmentationDetector` 类继承SmellDetector：实现detect()方法计算Pipeline的平均连贯性（连续相同模块类型的节点数），若存在过多小片段（如频繁的模块切换）则生成SmellInstance

- [x] 6.7 实现可复现类Smell检测器（3种）
     【目标对象】`src/smells/reproducibility_detectors.py::HardcodedParametersDetector类`, `src/smells/reproducibility_detectors.py::LackOfVersionControlDetector类`, `src/smells/reproducibility_detectors.py::NonDeterministicOrderDetector类`
     【修改目的】检测Hard-coded Parameters, Lack of Version Control, Non-deterministic Order
     【修改方式】定义检测器类，检查代码中的可复现性风险点
     【相关依赖】`src/smells/detector.py`::SmellDetector、`src/core/parser.py`::ASTParser
     【修改内容】
        - 定义 `HardcodedParametersDetector` 类继承SmellDetector：实现detect()方法识别超参数位置的硬编码字面量（如max_depth=5、n_estimators=100），检查AST中的ast.Constant节点出现在API调用keywords中，生成SmellInstance
        - 定义 `LackOfVersionControlDetector` 类继承SmellDetector：实现detect()方法检查是否包含库版本固定信息（requirements.txt是否在项目中、代码中是否有==版本号约束），若缺失则生成SmellInstance
        - 定义 `NonDeterministicOrderDetector` 类继承SmellDetector：实现detect()方法检查对set、dict等无序数据结构的遍历操作（for x in dict.values()），分析排序依赖操作是否缺少显式排序（sorted），生成SmellInstance

- [x] 6.8 实现检测器注册和调用机制
     【目标对象】`src/smells/detector.py::DetectorRegistry类`
     【修改目的】管理所有检测器，提供统一的调用接口
     【修改方式】定义DetectorRegistry类，实现注册器模式
     【相关依赖】所有*_detectors.py文件中的检测器类
     【修改内容】
        - 定义 `DetectorRegistry` 类：在__init__中初始化self.detectors = {}字典和self.categories = {}分类映射
        - 实现 `register(self, detector_class: Type[SmellDetector]) -> None` 方法：将detector类注册到detectors字典，按照SmellCategory分类
        - 实现 `get_detector(self, smell_type: str) -> SmellDetector` 方法：返回指定Smell类型的检测器实例
        - 实现 `detect_all(self, pipeline_graph: PipelineGraph, module_sequence: List[ModuleType]) -> List[SmellInstance]` 方法：依次调用所有注册的检测器，收集所有SmellInstance，使用set()去重（基于location和smell_type）
        - 实现 `detect_by_category(self, category: str, pipeline_graph, module_sequence) -> List[SmellInstance]` 方法：只调用指定类别的检测器
        - 使用类装饰器@register_detector自动化注册过程

### Phase 7: 报告生成器 (Report Generator) 实现
- [x] 7.1 实现文本报告生成器
     【目标对象】`src/core/reporter.py::TextReporter类`
     【修改目的】生成人类可读的文本格式检测报告
     【修改方式】定义TextReporter类，格式化输出检测结果
     【相关依赖】`src/smells/detector.py`::DetectionResult
     【修改内容】
        - 定义 `TextReporter` 类：在__init__中接收DetectionResult
        - 实现 `generate_report(self) -> str` 方法：按照Markdown格式生成报告，包含Pipeline概览、按类别分组的Smell列表（每个Smell显示位置、描述、严重性）、代码片段高亮
        - 实现 `save_report(self, output_path: str) -> None` 方法：将生成的报告写入文件
        - 实现 `print_summary(self) -> None` 方法：输出统计摘要（总Smell数、各类别数量、严重性分布）

- [x] 7.2 实现JSON报告生成器
     【目标对象】`src/core/reporter.py::JSONReporter类`
     【修改目的】生成机器可读的结构化报告
     【修改方式】定义JSONReporter类，序列化为JSON格式
     【相关依赖】`src/smells/detector.py`::DetectionResult
     【修改内容】
        - 定义 `JSONReporter` 类：在__init__中接收DetectionResult
        - 实现 `generate_report(self) -> Dict` 方法：将DetectionResult转换为JSON兼容的字典，使用json.dumps()序列化，包含Pipeline信息、完整的Smell列表
        - 实现 `save_report(self, output_path: str, indent: int = 2) -> None` 方法：将JSON写入文件，使用参数控制格式化缩进

- [x] 7.3 实现可视化报告生成器
     【目标对象】`src/core/reporter.py::VisualReporter类`
     【修改目的】生成Pipeline图和Smell的可视化展示
     【修改方式】定义VisualReporter类，使用graphviz绘制Pipeline图
     【相关依赖】`src/core/pipeline.py`::PipelineGraph、graphviz>=0.20
     【修改内容】
        - 定义 `VisualReporter` 类：在__init__中接收PipelineGraph和DetectionResult
        - 实现 `generate_pipeline_graph(self, output_path: str) -> None` 方法：使用graphviz.Digraph()实例，为每个Pipeline节点添加节点（使用label、shape、color属性），根据edges添加有向边，导出为PNG/SVG格式
        - 实现 `highlight_smells(self, digraph: Digraph, smells: List[SmellInstance]) -> None` 方法：遍历smells，将受影响的节点颜色按照严重性设置（CRITICAL=红色、HIGH=橙色、MEDIUM=黄色、LOW=绿色）
        - 实现 `generate_pie_chart(self, output_path: str) -> None` 方法：使用matplotlib绘制Smell严重性饼图

### Phase 8: 基线方法实现
- [x] 8.1 实现关键词检测基线
     【目标对象】`src/baseline/keyword_detector.py::KeywordBaseline类`
     【修改目的】实现基于关键词的简单Smell检测（Baseline 1）
     【修改方式】定义KeywordBaseline类，基于正则表达式模式匹配
     【相关依赖】`src/core/parser.py`::ASTParser、Python标准库re
     【修改内容】
        - 在模块级别定义 `PATTERNS` 字典：数据结构为{Smell类型: 正则表达式模式}，例如{'DATA_LEAKAGE': r'(fit|transform).*\n.*train_test_split', 'MISSING_RANDOM_SEED': r'train_test_split.*random_state\s*='}
        - 定义 `KeywordBaseline` 类：在__init__中初始化PATTERNS、re.compile()预编译正则
        - 实现 `detect(self, file_path: str) -> List[SmellInstance]` 方法：读取源文件内容，对每个pattern应用re.search(pattern, code)，若匹配则生成SmellInstance（记录匹配内容和位置）
        - 实现 `convert_to_detection_result(self, file_path: str, smells: List[SmellInstance]) -> DetectionResult` 方法：将基线结果转换为标准DetectionResult格式

- [x] 8.2 实现简单启发式规则基线
     【目标对象】`src/baseline/heuristic_detector.py::HeuristicBaseline类`
     【修改目的】实现基于简单规则的检测方法（Baseline 2）
     【修改方式】定义HeuristicBaseline类，定义if-else规则
     【相关依赖】`src/core/parser.py`::ASTParser、`src/core/parser.py`::APIExtractor
     【修改内容】
        - 在模块级别定义 `RULES` 常量：规则列表，每个规则定义为{'name': str, 'condition': callable, 'severity': str}
        - 定义 `HeuristicBaseline` 类：在__init__中初始化RULES
        - 实现 `detect(self, pipeline_graph, module_sequence) -> List[SmellInstance]` 方法：遍历RULES，对每个规则调用condition函数并传入pipeline和module_sequence参数，若condition返回True则生成对应的SmellInstance
        - 定义规则示例：RULE_MISSING_RANDOM_SEED = {'name': 'Missing Random Seed', 'condition': lambda p, m: True if check_no_random_state(p) else False, 'severity': 'HIGH'}

- [x] 8.3 集成SonarQube API（模拟）
     【目标对象】`src/baseline/sonarqube_adapter.py::SonarQubeBaseline类`
     【修改目的】模拟SonarQube的检测结果（Baseline 3）
     【修改方式】定义SonarQubeBaseline类，映射SonarQube规则到Pipeline Smell
     【相关依赖】`src/core/parser.py`::ASTParser、`src/smells/taxonomy.py`::PipelineSmell
     【修改内容】
        - 在模块级别定义 `SONARQUBE_RULES` 字典：映射SonarQube规则ID到Pipeline Smell，例如{'python:S1134': 'HARDCODED_PARAMETERS', 'python:S1172': 'REDUNDANT_OPERATION'}
        - 定义 `SonarQubeBaseline` 类：在__init__中初始化规则映射
        - 实现 `detect(self, file_path: str) -> List[SmellInstance]` 方法：模拟调用SonarQube API（或基于静态规则直接映射），对每个检查出的SonarQube问题转换对应的Pipeline Smell，生成SmellInstance
        - 实现 `convert_result(self, sonarqube_issue) -> SmellInstance` 方法：将SonarQube issue格式转换为标准SmellInstance

- [x] 8.4 集成PMD适配器（模拟）
     【目标对象】`src/baseline/pmd_adapter.py::PMDBaseline类`
     【修改目的】模拟PMD的检测结果（Baseline 4）
     【修改方式】定义PMDBaseline类，映射PMD规则到Pipeline Smell
     【相关依赖】`src/core/parser.py`::ASTParser、`src/smells/taxonomy.py`::PipelineSmell
     【修改内容】
        - 在模块级别定义 `PMD_RULES` 字典：映射PMD规则key到Pipeline Smell
        - 定义 `PMDBaseline` 类：在__init__中初始化规则映射
        - 实现 `detect(self, file_path: str) -> List[SmellInstance]` 方法：模拟调用PMD检测API，将PMD规则违规转换为Pipeline Smell，生成SmellInstance
        - 实现 `convert_result(self, pmd_issue) -> SmellInstance` 方法：将PMD issue格式转换为标准SmellInstance

### Phase 9: Ground Truth数据集构建
- [ ] 9.1 设计标注工具和数据存储格式
     【目标对象】`tools/annotation_tool.py::AnnotationToolCLI类`, `data/ground_truth/format.md`
     【修改目的】提供标注工具和标准化的数据存储格式
     【修改方式】定义JSON Schema和CLI工具，使用click库
     【相关依赖】click>=8.0、`src/core/pipeline.py`::PipelineGraph
     【修改内容】
        - 创建 `data/ground_truth/format.md` 文档，定义Ground Truth JSON Schema：包含pipeline_id(str)、file_path(str)、operations(List[Dict])和smells(List[Dict])
        - 定义operations字段格式：每个operation包含node_id、line_number、operation_type、api_name、inputs、outputs
        - 定义smells字段格式：每个smell包含smell_type、location（line_number）、severity、annotator
        - 定义 `AnnotationToolCLI` 类：实现init()命令（初始化空标注文件）、load()命令（加载待标注Pipeline）、annotate()命令（交互式标注，选择Smell类型和位置）、export()命令（导出标注结果为JSON）、validate()命令（检查JSON格式）
        - 实现 `detect_conflicts(smells: List[Smell]) -> List[Conflict]` 方法：比较多个标注者的结果，识别冲突（相同位置Smell类型不同），输出Cohen's Kappa计算逻辑

- [ ] 9.2 实现GitHub数据收集脚本
     【目标对象】`tools/github_collector.py::GitHubCollector类`
     【修改目的】从GitHub搜索和下载包含机器学习代码的仓库
     【修改方式】定义GitHubCollector类，使用GitHub REST API
     【相关依赖】gitpython>=3.1、Python标准库os、pathlib、json
     【修改内容】
        - 定义 `GitHubCollector` 类：在__init__中初始化search_keywords列表（['machine learning', 'pandas', 'scikit-learn']）、data_dir('data/raw/repos/')
        - 实现 `search_repositories(self, query: str, min_stars: int) -> List[RepoInfo]` 方法：构造GitHub搜索URL（https://api.github.com/search/repositories），解析JSON响应，过滤stars>=min_stars的仓库，返回仓库URL、描述、stars
        - 实现 `clone_repository(self, repo_url: str, local_path: str) -> None` 方法：使用git.Repo.clone_from(repo_url, local_path)克隆仓库，捕获GitError处理失败情况
        - 实现 `collect_batch(self, num_repos: int) -> None` 方法：循环搜索和克隆num_repos个仓库，保存到data/raw/repos/{owner}-{name}/目录

- [ ] 9.3 实现Pipeline提取和筛选脚本
     【目标对象】`tools/pipeline_extractor.py::PipelineExtractorScript类`
     【修改目的】从收集的Python文件中提取含Pipeline的脚本
     【修改方式】定义脚本类，调用Pipeline Extractor解析并筛选
     【相关依赖】`src/core/pipeline.py`::PipelineGraph、`src/core/parser.py`::ASTParser
     【修改内容】
        - 定义 `PipelineExtractorScript` 类：在__init__中初始化source_dir('data/raw/repos/')、output_dir('data/ground_truth/candidates/')
        - 实现 `extract_from_directory(self, directory: str) -> List[PipelineInfo]` 方法：os.walk()遍历目录，筛选*.py文件，调用extract_from_file()
        - 实现 `extract_from_file(self, file_path: str) -> Optional[PipelineInfo]` 方法：调用ASTParser.parse_file()解析，调用APIExtractor提取API调用，若提取的操作数量>=3则保存Pipeline信息
        - 实现 `save_candidates(self, pipelines: List[PipelineInfo]) -> None` 方法：将每个Pipeline保存为JSON文件到candidates/{pipeline_id}.json

- [ ] 9.4 构建Ground Truth标注数据集
     【目标对象】`data/ground_truth/gold_standard::gold_standard.json`
     【修改目的】创建200-300个Pipeline的人工标注数据
     【修改方式】使用标注工具进行人工标注，计算Kappa系数
     【相关依赖】`tools/annotation_tool.py`::AnnotationToolCLI、`tools/pipeline_extractor.py`::PipelineExtractorScript
     【修改内容】
        - 操作步骤：从candidates目录随机选取200-300个Pipeline JSON文件，使用AnnotationToolCLI进行2名标注者独立标注（模拟生成两份标注结果）
        - 标注内容：pipeline_id、file_path、operations（完整操作列表）、smells（每个Smell包含smell_type、line_number、severity）
        - 实现 `calculate_cohens_kappa(annotator1, annotator2) -> float` 方法：计算两名标注者的一致性Kappa系数，确保Kappa>0.7
        - 实现 `resolve_conflicts(annotator1, annotator2) -> GoldStandard` 方法：讨论解决冲突Smell或采纳多数意见，生成最终的gold_standard.json

### Phase 10: 评估框架实现
- [ ] 10.1 实现评估指标计算模块
     【目标对象】`src/evaluation/metrics.py::MetricsCalculator类`
     【修改目的】计算Precision, Recall, F1-score
     【修改方式】定义MetricsCalculator类，基于TP/FP/FN/TN计数
     【相关依赖】无
     【修改内容】
        - 定义 `MetricsCalculator` 类：在__init__中初始化计数器self.tp=0、self.fp=0、self.fn=0、self.tn=0
        - 实现 `calculate_precision(self) -> float` 方法：返回self.tp/(self.tp+self.fp)，处理除零返回0.0
        - 实现 `calculate_recall(self) -> float` 方法：返回self.tp/(self.tp+self.fn)，处理除零返回0.0
        - 实现 `calculate_f1(self) -> float` 方法：返回2*precision*recall/(precision+recall)，返回精度保留3位小数
        - 实现 `update_counts(self, predicted, ground_truth) -> None` 方法：比较预测结果和事实，更新TP/FP/FN计数（使用结果匹配算法判断）
        - 实现 `get_confusion_matrix(self) -> Dict` 方法：返回{'TP': self.tp, 'FP': self.fp, 'FN': self.fn, 'TN': self.tn}

- [ ] 10.2 实现检测结果匹配算法
     【目标对象】`src/evaluation/evaluation.py::ResultMatcher类`
     【修改目的】将检测结果与Ground Truth进行匹配，计算TP/FP/FN
     【修改方式】定义ResultMatcher类，基于Smell类型和位置模糊匹配
     【相关依赖】`src/evaluation/metrics.py`::MetricsCalculator
     【修改内容】
        - 定义 `ResultMatcher` 类：在__init__中接收predicted_smells和ground_truth_smells
        - 实现 `match_results(self, distance_threshold: int = 3) -> MatchResult` 方法：遍历ground_truth_smells，查找predicted_smells中相同Smell类型且line_number距离<=threshold的，标记为TP，未匹配的为FN，predicted中剩余未匹配的为FP
        - 实现 `calculate_line_distance(loc1: Location, loc2: Location) -> int` 方法：返回两个位置的行号差值abs(loc1.line_number - loc2.line_number)
        - 实现 `get_unmatched_predictions(self) -> List[SmellInstance]` 方法：返回所有FP列表
        - 实现 `get_missed_ground_truth(self) -> List[SmellInstance]` 方法：返回所有FN列表

- [ ] 10.3 实现多方法对比评估框架
     【目标对象】`src/evaluation/evaluation.py::ComparativeEvaluator类`
     【修改目的】对比本方法和所有基线方法的性能
     【修改方式】定义ComparativeEvaluator类，运行所有检测器计算指标
     【相关依赖】`src/evaluation/metrics.py`::MetricsCalculator、所有检测器和基线类
     【修改内容】
        - 定义 `ComparativeEvaluator` 类：在__init__中接收ground_truth、所有检测器列表
        - 实现 `evaluate_method(self, method_name: str, detector, ground_truth) -> EvaluationResult` 方法：调用detector.detect()获取predicted，使用ResultMatcher.match_results()计算匹配，使用MetricsCalculator计算P/R/F1，返回结果字典
        - 实现 `compare_all_methods(self) -> ComparisonTable` 方法：依次运行本方法（Pipeline-aware Detection）和所有基线方法（Keyword、Heuristic、SonarQube、PMD），收集所有P/R/F1结果生成对比表格字典
        - 实现 `get_best_method(self, metric: str) -> str` 方法：按指定指标（precision/recall/f1）排序，返回最佳方法名称

- [ ] 10.4 实现统计分析模块
     【目标对象】`src/evaluation/statistics.py::StatisticalTest类`
     【修改目的】进行统计显著性检验（Wilcoxon signed-rank test）
     【修改方式】定义StatisticalTest类，使用scipy.stats进行检验
     【相关依赖】scipy>=1.10
     【修改内容】
        - 定义 `StatisticalTest` 类：在__init__中初始化
        - 实现 `prepare_sample_metrics(self, method_results: List[EvaluationResult], metric: str) -> List[float]` 方法：从结果列表中提取指定指标的值（如多个Pipeline的precision）
        - 实现 `perform_wilcoxon_test(self, sample1: List[float], sample2: List[float]) -> TestResult` 方法：调用scipy.stats.wilcoxon(sample1, sample2)，返回statistic和p-value
        - 实现 `is_significant(self, p_value: float, alpha: float = 0.05) -> bool` 方法：判断p_value < alpha则返回True表示有显著差异
        - 实现 `format_test_result(self, test_result: TestResult) -> str` 方法：格式化输出为字符串，显示Z-statistic和p-value及显著性结论

### Phase 11: 实验脚本和结果分析
- [ ] 11.1 实现RQ1实验脚本（准确性对比）
     【目标对象】`experiments/rq1_accuracy.py::run_rq1_experiment()函数`
     【修改目的】执行RQ1实验：对比本方法与基线的Precision/Recall/F1
     【修改方式】定义实验函数，加载Gold Standard，运行所有检测器，计算指标
     【相关依赖】`src/evaluation/evaluation.py`::ComparativeEvaluator、`data/ground_truth/gold_standard.json`
     【修改内容】
        - 定义 `load_ground_truth() -> List[GoldStandardItem]` 函数：从gold_standard.json读取数据，返回Pipeline列表
        - 定义 `run_rq1_experiment()` 主函数：加载ground_truth，初始化ComparativeEvaluator，依次调用evaluate_method()评估本方法和4个基线方法，收集所有P/R/F1结果为字典
        - 定义 `save_results(results: Dict, output_path: str)` 函数：使用json.dump()保存结果到experiments/results/rq1_results.json
        - 定义 `print_comparison_table(results: Dict)` 函数：打印格式化的对比表格，显示每个方法的Precision、Recall、F1

- [ ] 11.2 实现RQ2实验脚本（检测能力对比）
     【目标对象】`experiments/rq2_coverage.py::run_rq2_experiment()函数`
     【修改目的】执行RQ2实验：对比不同方法检测的Smell类型数量
     【修改方式】定义实验函数，统计每个方法能检测到的Smell类型
     【相关依赖】所有检测器和基线类、`src/smells/taxonomy.py`::所有Smell类型
     【修改内容】
        - 定义 `get_all_smell_types() -> List[str]` 函数：从taxonomy.py中提取所有Smell类型名称
        - 定义 `run_rq2_experiment()` 主函数：初始化所有检测器和基线，对每个方法调用detect_all()并收集检测到的Smell类型集合，构建覆盖矩阵（方法xSmell类型）
        - 定义 `calculate_coverage_stats(coverage_matrix: Dict) -> Dict` 函数：计算每个方法检测到的Smell类型数量，列出本方法独有的Smell类型
        - 定义 `generate_heatmap_data(coverage_matrix: Dict) -> List[List[int]]` 函数：将覆盖矩阵转换为热图数据格式的二维列表
        - 定义 `save_results(results: Dict, output_path: str)` 函数：保存到experiments/results/rq2_results.json

- [ ] 11.3 实现结果分析和可视化脚本
     【目标对象】`experiments/analysis.py::AnalysisVisualizer类`
     【修改目的】生成实验结果的可视化图表（柱状图、箱线图等）
     【修改方式】定义AnalysisVisualizer类，使用matplotlib和seaborn绘图
     【相关依赖】`experiments/results/`、matplotlib>=3.6、seaborn>=0.12
     【修改内容】
        - 定义 `AnalysisVisualizer` 类：在__init__中初始化figure大小、字体设置
        - 实现 `plot_prf_comparison(self, rq1_results: Dict, output_path: str)` 方法：使用matplotlib.bar()绘制分组柱状图，X轴为方法名称，Y轴为P/R/F1值，使用不同颜色区分三个指标，添加图例和标题，保存为PNG
        - 实现 `plot_coverage_heatmap(self, rq2_results: Dict, output_path: str)` 方法：使用seaborn.heatmap()绘制Smell覆盖热图，X轴为Smell类型，Y轴为方法名称，使用颜色深浅表示是否检测到，保存为PNG
        - 实现 `plot_smell_distribution(self, results: Dict, output_path: str)` 方法：绘制各方法检测到的Smell类别分布，使用堆叠柱状图展示不同严重性和类别的数量

- [ ] 11.4 实现LaTeX表格和报告生成
     【目标对象】`experiments/report_generator.py::ReportGenerator类`
     【修改目的】生成实验结果的LaTeX表格和总结报告
     【修改方式】定义ReportGenerator类，格式化输出LaTeX和Markdown
     【相关依赖】`experiments/results/`、`experiments/figures/`
     【修改内容】
        - 定义 `ReportGenerator` 类：在__init__中加载rq1_results.json和rq2_results.json
        - 实现 `generate_latex_table_rq1(self) -> str` 方法：生成RQ1的LaTeX表格代码，使用tabular环境，列为Method、Precision、Recall、F1，每行对应一个方法，保留3位小数
        - 实现 `generate_latex_table_rq2(self) -> str` 方法：生成RQ2的LaTeX表格，列为Smell Type、本方法、Keyword、Heuristic、SonarQube、PMD，每行对应一个Smell类型
        - 实现 `generate_markdown_summary(self) -> str` 方法：生成总结报告的Markdown文本，包含关键发现、排名结果、统计显著性结论
        - 实现 `save_report(self, tex_path: str, md_path: str) -> None` 方法：将LaTeX表格写入report.tex，将Markdown总结写入report.md

### Phase 12: 文档和使用工具
- [x] 12.1 编写项目README
      【目标对象】`README.md`
      【修改目的】提供项目介绍、安装和使用指南
      【修改方式】编写Markdown文档
      【相关依赖】无
      【修改内容】
         - 在README.md中编写项目简介和研究目标：说明本研究聚焦于Pipeline级别的代码异味检测，介绍18种Smell类型
         - 编写系统架构图：使用Mermaid或ASCII图表展示Code Parser → Pipeline Extractor → Module Classifier → Smell Detector → Report Generator流程
         - 编写安装步骤：说明运行pip install -r requirements.txt，列出核心依赖
         - 编写使用示例：
           * 命令行使用示例：python -m src.cli detect example_pipeline.py --output report.json
           * Python API使用示例：导入PipelineGraph、DetectorRegistry，调用detect_all()
         * 实验运行指南：说明如何运行experiments/rq1_accuracy.py执行RQ1实验

- [ ] 12.2 编写API文档
     【目标对象】`docs/api_reference.md`
     【修改目的】提供核心模块的API文档
     【修改方式】编写Markdown格式的API参考
     【相关依赖】所有核心模块
     【修改内容】
        - Code Parser API文档：列出ASTParser类的方法（parse_file、parse_code、extract_***）、参数说明和返回值类型
        - Pipeline Extractor API文档：列出PipelineGraph类（add_node、add_edge、build_from_dependencies、topological_sort）、PipelineExtractor类的方法
        - Module Classifier API文档：列出ModuleClassifier类（classify_node、classify_pipeline）和ModuleBoundaryDetector类的方法
        - Smell Detector API文档：列出SmellDetector基类（detect抽象方法）、各检测器子类的detect实现
        - Evaluation API文档：列出MetricsCalculator、ResultMatcher、ComparativeEvaluator、StatisticalTest的公有方法

- [ ] 12.3 编写实验文档
     【目标对象】`docs/experiments.md`
     【修改目的】详细描述实验设计和复现步骤
     【修改方式】编写Markdown文档
     【相关依赖】所有实验脚本
     【修改内容】
        - 数据集构建过程：说明如何使用github_collector.py从GitHub收集200-300个ML仓库，如何使用pipeline_extractor.py提取Pipeline，如何使用annotation_tool.py进行人工标注
        - Ground Truth标注方法：说明标注规范、Cohen's Kappa计算流程（Kappa>0.7）、冲突解决策略
        - RQ1/RQ2实验设计：说明RQ1对比准确性（P/R/F1），RQ2对比覆盖能力（能检测到的Smell类型），列出基线方法（Keyword、Heuristic、SonarQube、PMD）
        - 结果解读：说明如何查看experiments/results/目录下的JSON结果，如何解读experiments/figures/目录下的可视化图表
        - 复现指南：提供step-by-step步骤让研究者复现实验，包括命令序列

- [ ] 12.4 编写Smell Catalog参考文档
     【目标对象】`docs/smell_catalog.md`
     【修改目的】详细说明所有15-20种Pipeline Smell的定义和示例
     【修改方式】编写Markdown文档，按类别组织
     【相关依赖】`src/smells/taxonomy.py`::所有Smell定义
     【修改内容】
        - 为每种Smell编写一个文档小节，包含：
          * 正式定义：Smell的语义说明
          * 检测逻辑说明：如何识别该Smell
          * 代码示例：展示有Smell的代码片段和无Smell的修复后代码
          * 修复建议：给出具体的改进建议
          * 相关文献链接：引用相关论文或参考资料
        - 按六大类别组织内容：Order-related、Redundancy-related、Missing-related、Performance-related、Structure-related、Reproducibility-related

- [x] 12.5 实现命令行接口（CLI）
      【目标对象】`src/cli.py`::命令组函数
     【修改目的】提供友好的命令行工具
     【修改方式】使用click库定义CLI命令，配置setup.py
     【相关依赖】click>=8.0、所有核心模块
     【修改内容】
        - 在src/cli.py中定义main()命令组，使用click.group()装饰器
        - 实现 `pipeline-smell detect [FLAGS] FILEPATH` 命令：使用click.argument()定义参数，调用ASTParser解析文件，调用PipelineGraph构建Pipeline，调用DetectorRegistry.detect_all()检测Smell，调用TextReporter生成报告，使用--output指定输出文件，使用--format(text|json)指定格式
        - 实现 `pipeline-smell batch [FLAGS] DIRECTORY` 命令：遍历目录下所有.py文件，批量检测并汇总结果
        - 实现 `pipeline-smell evaluate [FLAGS]` 命令：运行RQ1/RQ2实验，调用experiments/rq1_accuracy.py和rq2_coverage.py的函数
        - 实现 `pipeline-smell report [FLAGS] RESULT_FILE` 命令：从result JSON生成可视化报告，调用AnalysisVisualizer生成图表
        - 在setup.py的[options.entry_points]部分配置console_scripts：pipeline-smell=src.cli:main
