"""
代码解析器模块

提供AST解析、API调用提取、控制流分析等功能，用于检测代码异味。
"""

import ast
from typing import Any, Dict, List, Optional, Set

from src.core.logger import Logger


# 关键API常量，用于识别数据管道中的常见操作
KEY_APIS = {
    'pandas': ['read_csv', 'fillna', 'dropna', 'drop_duplicates', 'merge', 'groupby'],
    'sklearn.preprocessing': ['StandardScaler', 'MinMaxScaler'],
    'sklearn.model_selection': ['train_test_split'],
    'sklearn': ['fit', 'transform', 'predict', 'score']
}


class ASTParser:
    """AST解析器
    
    提供Python代码的AST解析功能，包括文件解析、导入提取、函数提取、类提取等。
    """
    
    def __init__(self) -> None:
        """初始化AST解析器"""
        self._logger = Logger.setup('ast_parser', 'logs/ast_parser.log')
    
    def parse_file(self, file_path: str) -> Optional[ast.Module]:
        """解析Python文件为AST
        
        Args:
            file_path: Python文件路径
            
        Returns:
            AST模块节点，如果解析失败则返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return ast.parse(code, filename=file_path)
        except SyntaxError as e:
            self._logger.error(f"语法错误: {file_path} - {e}")
            return None
        except UnicodeDecodeError as e:
            self._logger.error(f"编码错误: {file_path} - {e}")
            return None
        except FileNotFoundError as e:
            self._logger.error(f"文件不存在: {file_path} - {e}")
            return None
    
    def parse_code(self, code: str) -> Optional[ast.Module]:
        """解析代码字符串为AST
        
        Args:
            code: Python代码字符串
            
        Returns:
            AST模块节点，如果解析失败则返回None
        """
        try:
            return ast.parse(code)
        except SyntaxError as e:
            self._logger.error(f"代码解析错误: {e}")
            return None
    
    def extract_imports(self, node: ast.Module) -> List[Dict[str, Any]]:
        """提取模块的导入信息
        
        Args:
            node: AST模块节点
            
        Returns:
            导入信息列表，每个元素包含'module'和'imports'键
        """
        imports = []
        for item in node.body:
            if isinstance(item, ast.Import):
                for alias in item.names:
                    imports.append({
                        'module': alias.name,
                        'imports': [alias.asname if alias.asname else alias.name]
                    })
            elif isinstance(item, ast.ImportFrom):
                module_name = item.module if item.module else ''
                imported_names = []
                for alias in item.names:
                    imported_names.append(alias.asname if alias.asname else alias.name)
                imports.append({
                    'module': module_name,
                    'imports': imported_names
                })
        return imports
    
    def extract_functions(self, node: ast.Module) -> List[Dict[str, Any]]:
        """提取模块的函数定义
        
        Args:
            node: AST模块节点
            
        Returns:
            函数信息列表，每个元素包含'name', 'args', 'returns', 'line_no'键
        """
        functions = []
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [arg.arg for arg in item.args.args]
                returns = None
                if item.returns and hasattr(item.returns, 'id'):
                    returns = item.returns.id
                elif item.returns and hasattr(item.returns, 'attr'):
                    returns = item.returns.attr
                
                functions.append({
                    'name': item.name,
                    'args': args,
                    'returns': returns,
                    'line_no': item.lineno,
                    'is_async': isinstance(item, ast.AsyncFunctionDef)
                })
        return functions
    
    def extract_classes(self, node: ast.Module) -> List[Dict[str, Any]]:
        """提取模块的类定义
        
        Args:
            node: AST模块节点
            
        Returns:
            类信息列表，每个元素包含'name', 'bases', 'methods', 'line_no'键
        """
        classes = []
        for item in node.body:
            if isinstance(item, ast.ClassDef):
                bases = []
                for base in item.bases:
                    if hasattr(base, 'id'):
                        bases.append(base.id)
                    elif hasattr(base, 'attr'):
                        bases.append(base.attr)
                
                methods = []
                for sub_item in item.body:
                    if isinstance(sub_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(sub_item.name)
                
                classes.append({
                    'name': item.name,
                    'bases': bases,
                    'methods': methods,
                    'line_no': item.lineno
                })
        return classes


class APIExtractor:
    """API提取器
    
    用于识别和提取代码中的关键API调用，特别关注数据处理和机器学习库。
    """
    
    def __init__(self, key_apis: Optional[Dict[str, List[str]]] = None) -> None:
        """初始化API提取器
        
        Args:
            key_apis: 关键API字典，默认使用KEY_APIS
        """
        self._key_apis = key_apis if key_apis is not None else KEY_APIS
        self._logger = Logger.setup('api_extractor', 'logs/api_extractor.log')
    
    def extract_calls(self, node: ast.Module) -> List[Dict[str, Any]]:
        """提取代码中的所有API调用
        
        Args:
            node: AST模块节点
            
        Returns:
            API调用信息列表
        """
        api_calls = []
        for item in ast.walk(node):
            if isinstance(item, ast.Call):
                matched_api = self.match_api(item)
                if matched_api:
                    args_info = self.extract_args(item)
                    return_var = self.track_return_variable(item)
                    
                    api_calls.append({
                        **matched_api,
                        'args': args_info['args'],
                        'kwargs': args_info['kwargs'],
                        'return_var': return_var,
                        'line_no': item.lineno
                    })
        return api_calls
    
    def match_api(self, call_node: ast.Call) -> Optional[Dict[str, Any]]:
        """匹配关键API
        
        Args:
            call_node: AST调用节点
            
        Returns:
            匹配的API信息，包含'api_name', 'library', 'call_chain'键，如果未匹配则返回None
        """
        call_chain = self._extract_call_chain(call_node)
        if not call_chain:
            return None
        
        func_name = call_chain[-1]
        
        # 尝试匹配完整调用链
        for library, apis in self._key_apis.items():
            for api in apis:
                if func_name == api:
                    # 检查是否是方法调用（属性访问）
                    if len(call_chain) > 1:
                        # 方法调用，如 df.fillna()
                        return {
                            'api_name': api,
                            'library': library,
                            'call_chain': call_chain
                        }
                    else:
                        # 直接函数调用，如 pd.read_csv()
                        return {
                            'api_name': api,
                            'library': library,
                            'call_chain': call_chain
                        }
        
        return None
    
    def _extract_call_chain(self, call_node: ast.Call) -> List[str]:
        """递归提取调用链
        
        Args:
            call_node: AST调用节点
            
        Returns:
            调用链列表，例如 ['df', 'fillna', 'value_counts']
        """
        call_chain = []
        func = call_node.func
        
        while func:
            if isinstance(func, ast.Name):
                call_chain.insert(0, func.id)
                break
            elif isinstance(func, ast.Attribute):
                call_chain.insert(0, func.attr)
                func = func.value
            else:
                break
        
        return call_chain
    
    def extract_args(self, call_node: ast.Call) -> Dict[str, Any]:
        """提取API调用的参数信息
        
        Args:
            call_node: AST调用节点
            
        Returns:
            包含'args'和'kwargs'键的字典
        """
        args = []
        kwargs = {}
        
        # 提取位置参数
        for arg in call_node.args:
            arg_value = self._extract_arg_value(arg)
            args.append(arg_value)
        
        # 提取关键字参数
        for keyword in call_node.keywords:
            arg_name = keyword.arg
            arg_value = self._extract_arg_value(keyword.value)
            kwargs[arg_name] = arg_value
        
        return {
            'args': args,
            'kwargs': kwargs
        }
    
    def _extract_arg_value(self, arg_node: ast.AST) -> Any:
        """提取参数节点值
        
        Args:
            arg_node: AST表达式节点
            
        Returns:
            参数值
        """
        if isinstance(arg_node, ast.Name):
            return arg_node.id
        elif isinstance(arg_node, ast.Constant):
            return arg_node.value
        elif isinstance(arg_node, ast.Num):
            return arg_node.n
        elif isinstance(arg_node, ast.Str):
            return arg_node.s
        elif isinstance(arg_node, ast.List):
            return [self._extract_arg_value(item) for item in arg_node.elts]
        elif isinstance(arg_node, ast.Dict):
            keys = [self._extract_arg_value(k) for k in arg_node.keys]
            values = [self._extract_arg_value(v) for v in arg_node.values]
            return dict(zip(keys, values))
        else:
            return str(type(arg_node).__name__)
    
    def track_return_variable(self, call_node: ast.Call) -> Optional[str]:
        """跟踪API调用的返回值变量
        
        Args:
            call_node: AST调用节点
            
        Returns:
            返回值变量名，如果没有被赋值则返回None
        """
        # 这里需要额外的上下文信息来找到父节点
        # 由于AST节点不包含父节点引用，这里简化处理
        # 在实际使用中，需要遍历父节点来查找赋值关系
        return None


class ControlFlowAnalyzer:
    """控制流分析器
    
    用于分析代码的控制流结构，包括条件语句、循环和变量依赖关系。
    """
    
    def __init__(self) -> None:
        """初始化控制流分析器"""
        self._variable_definitions: Dict[str, List[int]] = {}
        self._logger = Logger.setup('control_flow_analyzer', 'logs/control_flow_analyzer.log')
    
    def analyze_control_flow(self, node: ast.Module) -> Dict[str, Any]:
        """分析代码的控制流结构
        
        Args:
            node: AST模块节点
            
        Returns:
            控制流信息，包含'if_blocks'和'loops'键
        """
        if_blocks = self.analyze_conditionals(node)
        loops = self.analyze_loops(node)
        
        return {
            'if_blocks': if_blocks,
            'loops': loops
        }
    
    def track_variable_usage(self, node: ast.Module) -> Dict[str, List[Dict[str, Any]]]:
        """跟踪变量的定义和使用情况
        
        Args:
            node: AST模块节点
            
        Returns:
            变量使用信息字典，键为变量名，值为使用信息列表
        """
        var_usage: Dict[str, List[Dict[str, Any]]] = {}
        
        for item in ast.walk(node):
            if isinstance(item, ast.Name):
                var_name = item.id
                if var_name not in var_usage:
                    var_usage[var_name] = []
                
                if isinstance(item.ctx, ast.Store):
                    var_type = 'store'
                elif isinstance(item.ctx, ast.Load):
                    var_type = 'load'
                else:
                    var_type = 'other'
                
                var_usage[var_name].append({
                    'line': item.lineno,
                    'type': var_type
                })
        
        return var_usage
    
    def analyze_loops(self, node: ast.Module) -> List[Dict[str, Any]]:
        """分析循环结构
        
        Args:
            node: AST模块节点
            
        Returns:
            循环信息列表
        """
        loops = []
        
        for item in node.body:
            if isinstance(item, ast.For):
                # 提取for循环变量
                if isinstance(item.target, ast.Name):
                    iter_var = item.target.id
                elif isinstance(item.target, ast.Tuple):
                    iter_var = [elt.id for elt in item.target.elts if isinstance(elt, ast.Name)]
                else:
                    iter_var = str(type(item.target).__name__)
                
                loops.append({
                    'type': 'for',
                    'iter_var': iter_var,
                    'line_no': item.lineno
                })
            elif isinstance(item, ast.While):
                loops.append({
                    'type': 'while',
                    'line_no': item.lineno
                })
            
            # 递归分析嵌套结构中的循环
            if hasattr(item, 'body'):
                nested_loops = self._analyze_loops_recursive(item)
                loops.extend(nested_loops)
        
        return loops
    
    def _analyze_loops_recursive(self, node: ast.AST) -> List[Dict[str, Any]]:
        """递归分析嵌套循环
        
        Args:
            node: AST节点
            
        Returns:
            嵌套循环信息列表
        """
        loops = []
        
        if hasattr(node, 'body'):
            for item in node.body:
                if isinstance(item, ast.For):
                    if isinstance(item.target, ast.Name):
                        iter_var = item.target.id
                    elif isinstance(item.target, ast.Tuple):
                        iter_var = [elt.id for elt in item.target.elts if isinstance(elt, ast.Name)]
                    else:
                        iter_var = str(type(item.target).__name__)
                    
                    loops.append({
                        'type': 'for',
                        'iter_var': iter_var,
                        'line_no': item.lineno
                    })
                elif isinstance(item, ast.While):
                    loops.append({
                        'type': 'while',
                        'line_no': item.lineno
                    })
                
                # 递归检查嵌套
                if hasattr(item, 'body'):
                    loops.extend(self._analyze_loops_recursive(item))
                if hasattr(item, 'orelse'):
                    for orelse_item in item.orelse:
                        loops.extend(self._analyze_loops_recursive(orelse_item))
        
        return loops
    
    def analyze_conditionals(self, node: ast.Module) -> List[Dict[str, Any]]:
        """分析条件语句结构
        
        Args:
            node: AST模块节点
            
        Returns:
            条件块信息列表
        """
        conditionals = []
        
        for item in node.body:
            if isinstance(item, ast.If):
                condition_text = self._extract_condition_text(item.test)
                
                conditionals.append({
                    'type': 'if',
                    'condition': condition_text,
                    'line_no': item.lineno,
                    'has_else': len(item.orelse) > 0
                })
            
            # 递归分析嵌套条件
            if hasattr(item, 'body'):
                nested_conditionals = self._analyze_conditionals_recursive(item)
                conditionals.extend(nested_conditionals)
        
        return conditionals
    
    def _analyze_conditionals_recursive(self, node: ast.AST) -> List[Dict[str, Any]]:
        """递归分析嵌套条件语句
        
        Args:
            node: AST节点
            
        Returns:
            嵌套条件信息列表
        """
        conditionals = []
        
        if hasattr(node, 'body'):
            for item in node.body:
                if isinstance(item, ast.If):
                    condition_text = self._extract_condition_text(item.test)
                    
                    conditionals.append({
                        'type': 'if',
                        'condition': condition_text,
                        'line_no': item.lineno,
                        'has_else': len(item.orelse) > 0
                    })
                
                # 递归检查嵌套
                if hasattr(item, 'body'):
                    conditionals.extend(self._analyze_conditionals_recursive(item))
                if hasattr(item, 'orelse'):
                    for orelse_item in item.orelse:
                        conditionals.extend(self._analyze_conditionals_recursive(orelse_item))
        
        return conditionals
    
    def _extract_condition_text(self, test_node: ast.AST) -> str:
        """提取条件表达式的文本表示
        
        Args:
            test_node: 条件表达式节点
            
        Returns:
            条件表达式的字符串表示
        """
        if isinstance(test_node, ast.Name):
            return test_node.id
        elif isinstance(test_node, ast.Compare):
            left = ast.dump(test_node.left)
            return f"compare({left})"
        elif isinstance(test_node, ast.UnaryOp):
            return f"unary({type(test_node.op).__name__})"
        else:
            return type(test_node).__name__
    
    def build_dependency_graph(self, api_calls: List[Dict], var_usage: Dict) -> Dict[str, Set[str]]:
        """构建变量依赖图
        
        Args:
            api_calls: API调用信息列表
            var_usage: 变量使用信息字典
            
        Returns:
            依赖图字典，键为变量名，值为依赖的变量集合
        """
        dependency_graph: Dict[str, Set[str]] = {}
        
        # 首先收集所有被赋值的变量（API调用的返回变量）
        output_vars = set()
        for call in api_calls:
            if call.get('return_var'):
                output_vars.add(call['return_var'])
        
        # 对每个API调用，分析其输入变量
        for call in api_calls:
            args = call.get('args', [])
            kwargs = call.get('kwargs', {})
            
            # 从参数中提取变量名
            input_vars = set()
            
            # 处理位置参数
            for arg in args:
                if isinstance(arg, str) and arg in var_usage:
                    input_vars.add(arg)
            
            # 处理关键字参数
            for var_name, value in kwargs.items():
                if isinstance(value, str) and value in var_usage:
                    input_vars.add(value)
            
            # 如果API调用有返回变量，则建立依赖关系
            return_var = call.get('return_var')
            if return_var and input_vars:
                if return_var not in dependency_graph:
                    dependency_graph[return_var] = set()
                
                for input_var in input_vars:
                    if input_var in output_vars:
                        dependency_graph[return_var].add(input_var)
        
        return dependency_graph
