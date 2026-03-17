"""
Pipeline提取器模块

提供Pipeline节点抽象、图构建算法和序列提取功能，用于识别和分析数据管道。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import networkx as nx
from networkx import NetworkXError

from src.core.logger import Logger


class OperationType(Enum):
    """操作类型枚举
    
    定义Pipeline中不同类型的操作，用于分类和识别节点的功能角色。
    """
    DATA_LOADING = "DATA_LOADING"
    DATA_CLEANING = "DATA_CLEANING"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    MODEL_OPERATION = "MODEL_OPERATION"
    VALIDATION = "VALIDATION"
    TRAIN_TEST_SPLIT = "TRAIN_TEST_SPLIT"
    AUXILIARY = "AUXILIARY"
    OTHER = "OTHER"


@dataclass
class PipelineNode:
    """Pipeline节点数据类
    
    表示Pipeline中的一个操作节点，包含操作类型、输入输出变量、代码位置等信息。
    """
    node_id: str
    operation_type: OperationType
    api_name: str
    inputs: List[str]
    outputs: List[str]
    line_number: int
    code_snippet: str
    location: str
    attributes: Dict[str, Any]
    
    @classmethod
    def from_api_call(cls, api_call: Dict[str, Any]) -> 'PipelineNode':
        """根据API调用信息创建PipelineNode
        
        Args:
            api_call: API调用信息字典
            
        Returns:
            PipelineNode实例
        """
        return cls(
            node_id=api_call.get('id', ''),
            operation_type=api_call.get('operation_type', OperationType.OTHER),
            api_name=api_call.get('api_name', ''),
            inputs=api_call.get('inputs', []),
            outputs=api_call.get('outputs', []),
            line_number=api_call.get('line_number', 0),
            code_snippet=api_call.get('code_snippet', ''),
            location=api_call.get('location', ''),
            attributes=api_call.get('attributes', {})
        )


class PipelineGraph:
    """Pipeline图构建器
    
    使用有向图表示Pipeline中的节点和数据流关系。
    """
    
    def __init__(self) -> None:
        """初始化Pipeline图"""
        self.graph = nx.DiGraph()
        self._logger = Logger.setup('pipeline_graph', 'logs/pipeline_graph.log')
    
    def add_node(self, node: PipelineNode) -> None:
        """向图中添加节点
        
        Args:
            node: 要添加的PipelineNode实例
        """
        self.graph.add_node(
            node.node_id,
            operation_type=node.operation_type,
            api_name=node.api_name,
            inputs=node.inputs,
            outputs=node.outputs,
            line_number=node.line_number,
            code_snippet=node.code_snippet,
            location=node.location,
            attributes=node.attributes
        )
        self._logger.debug(f"添加节点: {node.node_id}")
    
    def add_edge(self, source_id: str, target_id: str, edge_type: str, **kwargs) -> None:
        """在图中添加有向边
        
        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            edge_type: 边类型，可选值为'data_flow'、'control_flow'或'backward'
            **kwargs: 其他边属性
        """
        valid_edge_types = {'data_flow', 'control_flow', 'backward', 'data_dependency'}
        if edge_type not in valid_edge_types:
            raise ValueError(f"edge_type必须是{valid_edge_types}中的一个")
        
        edge_data = {'edge_type': edge_type}
        edge_data.update(kwargs)
        self.graph.add_edge(source_id, target_id, **edge_data)
        self._logger.debug(f"添加边: {source_id} -> {target_id} ({edge_type})")
    
    def topological_sort(self) -> List[str]:
        """对图进行拓扑排序
        
        Returns:
            按拓扑顺序排列的节点ID列表
            
        Raises:
            NetworkXError: 图中存在环时抛出
        """
        try:
            sorted_nodes = list(nx.topological_sort(self.graph))
            self._logger.debug(f"拓扑排序结果: {sorted_nodes}")
            return sorted_nodes
        except NetworkXError as e:
            self._logger.warning(f"图中存在环，无法进行拓扑排序: {e}")
            return list(self.graph.nodes())
    
    def get_execution_paths(self) -> List[List[str]]:
        """提取所有可能的执行路径
        
        Returns:
            执行路径列表，每个路径是一个节点ID列表
        """
        paths = []
        # 找到入度为0的节点（起始节点）
        start_nodes = [n for n, d in self.graph.in_degree() if d == 0]
        
        for start in start_nodes:
            # 找到出度为0的节点（结束节点）
            end_nodes = [n for n, d in self.graph.out_degree() if d == 0]
            
            for end in end_nodes:
                try:
                    all_simple_paths = list(nx.all_simple_paths(self.graph, start, end))
                    paths.extend(all_simple_paths)
                except NetworkXError:
                    continue
        
        self._logger.debug(f"提取到 {len(paths)} 条执行路径")
        return paths
    
    def get_node_by_id(self, node_id: str) -> Optional[PipelineNode]:
        """根据节点ID获取PipelineNode（从图中重建）
        
        Args:
            node_id: 节点ID
            
        Returns:
            PipelineNode对象，如果节点不存在返回None
        """
        node_data = self.graph.nodes.get(node_id)
        if not node_data:
            return None
        
        return PipelineNode(
            node_id=node_id,
            operation_type=node_data.get('operation_type', OperationType.OTHER),
            api_name=node_data.get('api_name', ''),
            inputs=node_data.get('inputs', []),
            outputs=node_data.get('outputs', []),
            line_number=node_data.get('line_number', 0),
            code_snippet=node_data.get('code_snippet', ''),
            location=node_data.get('location', ''),
            attributes=node_data.get('attributes', {})
        )
    
    def identify_branch_points(self) -> List[str]:
        """识别分支点（出度大于1的节点）
        
        Returns:
            分支点节点ID列表
        """
        branch_points = [n for n, d in self.graph.out_degree() if d > 1]
        self._logger.debug(f"识别到 {len(branch_points)} 个分支点: {branch_points}")
        return branch_points
    
    def identify_merge_points(self) -> List[str]:
        """识别汇合点（入度大于1的节点）
        
        Returns:
            汇合点节点ID列表
        """
        merge_points = [n for n, d in self.graph.in_degree() if d > 1]
        self._logger.debug(f"识别到 {len(merge_points)} 个汇合点: {merge_points}")
        return merge_points


class PipelineExtractor:
    """Pipeline提取器 - 主要接口类
    
    整合AST解析、Pipeline构建和提取功能，提供从源代码文件提取Pipeline的统一接口。
    """
    
    def __init__(self):
        """初始化Pipeline提取器"""
        self._logger = Logger.setup('pipeline_extractor', 'logs/pipeline_extractor.log')
    
    def extract_from_file(self, file_path: str) -> Optional[PipelineGraph]:
        """从Python文件提取Pipeline
        
        Args:
            file_path: 要处理的Python文件路径
            
        Returns:
            提取的PipelineGraph对象，如果未找到Pipeline则返回None
        """
        try:
            from src.core.parser import ASTParser
            
            # 1. 解析AST
            parser = ASTParser()
            ast_result = parser.parse_file(file_path)
            
            if not ast_result or not ast_result.api_calls:
                self._logger.debug(f"文件中未找到API调用: {file_path}")
                return None
            
            self._logger.info(f"解析到 {len(ast_result.api_calls)} 个API调用")
            
            # 2. 创建PipelineGraph
            pipeline_graph = PipelineGraph()
            
            # 3. 添加节点
            for api_call in ast_result.api_calls:
                node = PipelineNode.from_api_call(api_call)
                pipeline_graph.add_node(node)
            
            # 4. 构建边（数据依赖）
            for api_call in ast_result.api_calls:
                node_id = api_call.get('id', '')
                inputs = api_call.get('inputs', [])
                outputs = api_call.get('outputs', [])
                
                # 找到输入依赖的节点
                for var_name in inputs:
                    source_calls = self._find_variable_definition(ast_result.api_calls, var_name)
                    for source_call in source_calls:
                        if source_call and source_call.get('id') != node_id:
                            source_id = source_call.get('id', '')
                            pipeline_graph.add_edge(source_id, node_id,
                                                  edge_type='data_dependency',
                                                  variable=var_name)
            
            # 5. 验证Pipeline
            if pipeline_graph.graph.number_of_nodes() == 0:
                self._logger.warning(f"未构建Pipeline图: {file_path}")
                return None
            
            self._logger.info(f"成功构建Pipeline: {pipeline_graph.graph.number_of_nodes()} 个节点, "
                            f"{pipeline_graph.graph.number_of_edges()} 条边")
            
            return pipeline_graph
            
        except Exception as e:
            self._logger.error(f"提取Pipeline失败: {e}")
            import traceback
            self._logger.debug(traceback.format_exc())
            return None
    
    def _find_variable_definition(self, api_calls: List[Dict], var_name: str) -> List[Dict]:
        """查找变量定义的API调用
        
        Args:
            api_calls: 所有API调用列表
            var_name: 变量名
            
        Returns:
            定义该变量的API调用列表
        """
        definitions = []
        for call in api_calls:
            outputs = call.get('outputs', [])
            if var_name in outputs:
                definitions.append(call)
        return definitions
    
    def get_node(self, pipeline: PipelineGraph, node_id: str) -> Optional[PipelineNode]:
        """获取指定ID的节点
        
        Args:
            pipeline: PipelineGraph实例
            node_id: 节点ID
            
        Returns:
            PipelineNode对象，如果不存在返回None
        """
        return pipeline.graph.get_node_by_id(node_id)
    
    def get_nodes(self, pipeline: PipelineGraph) -> List[PipelineNode]:
        """获取所有节点
        
        Args:
            pipeline: PipelineGraph实例
            
        Returns:
            PipelineNode列表
        """
        return [pipeline.graph.get_node_by_id(node_id)
                for node_id in pipeline.graph.graph.nodes()]
