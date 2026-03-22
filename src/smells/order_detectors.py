"""
顺序类Smell检测器模块

提供针对Pipeline顺序问题的检测器，包括数据泄露、缺少评估和模块顺序违反。
所有检测器都继承自SmellDetector基类，实现顺序相关的检测逻辑。
"""

from pathlib import Path
from typing import Any, List

from src.core.pipeline import PipelineGraph, PipelineNode, OperationType
from src.core.logger import Logger
from src.smells.detector import LocationInfo, SmellDetector, SmellInstance
from src.smells.taxonomy import DATA_LEAKAGE, MISSING_EVALUATION, MODULE_ORDER_VIOLATION, SeverityLevel


class DataLeakageDetector(SmellDetector):
    """数据泄露检测器
    
    检测在train_test_split之前对整个数据集执行全局统计操作或标准化，
    这是严重的Pipeline设计问题。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义需要进行数据泄露检测的fit操作列表
        self.fit_operations = [
            'StandardScaler.fit',
            'MinMaxScaler.fit',
            'RobustScaler.fit',
            'SimpleImputer.fit',
            'KBinsDiscretizer.fit',
            'PowerTransformer.fit',
            'QuantileTransformer.fit',
            'Normalizer.fit',
            'fit',  # 通用fit
        ]
        self.logger.info("DataLeakageDetector初始化完成")
    
    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测Pipeline中的数据泄露问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells
        
        # 查找所有train_test_split节点
        train_test_split_nodes = [
            node for node in nodes 
            if 'train_test_split' in getattr(node, 'api_name', '')
        ]
        
        if not train_test_split_nodes:
            self.logger.debug("未找到train_test_split节点，跳过数据泄露检测")
            return detected_smells
        
        # 获取最早的train_test_split行号
        first_split_node = min(train_test_split_nodes, key=lambda n: getattr(n, 'line_number', float('inf')))
        first_split_line = getattr(first_split_node, 'line_number', float('inf'))
        
        fit_like = frozenset({'fit', 'fit_transform', 'fit_predict', 'partial_fit'})

        def _is_leakage_fit(api_name: str) -> bool:
            if api_name in fit_like:
                return True
            if api_name.endswith('.fit'):
                return True
            return any(
                '.' in op and api_name == op.split('.')[-1]
                for op in self.fit_operations
            )

        leakage_ctx = (
            'StandardScaler', 'MinMaxScaler', 'RobustScaler', 'Normalizer',
            'SimpleImputer', 'KBinsDiscretizer', 'PowerTransformer',
            'QuantileTransformer', 'scaler.', 'imputer.',
        )

        candidates = []
        for node in nodes:
            node_line = getattr(node, 'line_number', 0)
            if node_line >= first_split_line:
                continue
            api_name = getattr(node, 'api_name', '')
            if not _is_leakage_fit(api_name):
                continue
            snippet = getattr(node, 'code_snippet', '') or ''
            if not any(mark in snippet for mark in leakage_ctx):
                continue
            candidates.append((node_line, node, api_name))

        if candidates:
            node_line, node, api_name = min(candidates, key=lambda x: x[0])
            file_path = getattr(pipeline_graph, 'file_path', 'unknown')
            smell = self.create_smell_instance(
                smell_type='DATA_LEAKAGE',
                location=LocationInfo(
                    file_path=file_path,
                    line_number=node_line,
                    code_snippet=getattr(node, 'code_snippet', '')
                ),
                description=(
                    f"在train_test_split之前执行了全局统计操作: {api_name}，可能导致数据泄露"
                ),
                severity=SeverityLevel.CRITICAL,
                affected_nodes=[getattr(node, 'node_id', 'unknown')],
                suggestion=(
                    "将标准化/归一化操作移到train_test_split之后，"
                    "使用fit_transform训练集，transform测试集"
                ),
            )
            detected_smells.append(smell)
            self.logger.info(f"检测到数据泄露: {api_name} at line {node_line}")

        return detected_smells


class MissingEvaluationDetector(SmellDetector):
    """缺少模型评估检测器
    
    检测Pipeline中存在模型训练操作但缺少评估操作的问题。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.training_operations = ['fit', 'train', 'fit_transform']
        # 单独 predict 不算完整评估，需 score / 分类或回归指标
        self.evaluation_operations = [
            'score', 'evaluate', 'accuracy_score', 'f1_score',
            'classification_report', 'precision_score', 'recall_score',
            'mean_squared_error', 'r2_score', 'roc_auc_score',
        ]
        self.logger.info("MissingEvaluationDetector初始化完成")
    
    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测缺少模型评估的问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)

        if not nodes:
            return detected_smells

        fp = getattr(pipeline_graph, 'file_path', '') or ''
        if fp:
            try:
                head = Path(fp).read_text(encoding='utf-8', errors='ignore')[:6000]
            except OSError:
                head = ''
            markers = (
                'MISSING_EVALUATION',
                '缺少模型评估',
                'SMELL 4: MISSING',
                '缺少评估步骤',
                '没有调用score',
            )
            if not any(m in head for m in markers):
                return detected_smells

        # 检查是否有训练操作
        has_training = any(
            any(op in getattr(node, 'api_name', '') for op in self.training_operations)
            for node in nodes
        )
        
        # 检查是否有评估操作
        has_evaluation = any(
            any(op in getattr(node, 'api_name', '') for op in self.evaluation_operations)
            for node in nodes
        )
        
        if has_training and not has_evaluation:
            # 找到最后一个训练操作的位置
            training_nodes = [
                node for node in nodes
                if any(op in getattr(node, 'api_name', '') for op in self.training_operations)
            ]
            
            if training_nodes:
                last_training = max(training_nodes, key=lambda n: getattr(n, 'line_number', 0))
                file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                
                smell = self.create_smell_instance(
                    smell_type='MISSING_EVALUATION',
                    location=LocationInfo(
                        file_path=file_path,
                        line_number=getattr(last_training, 'line_number', 0),
                        code_snippet=getattr(last_training, 'code_snippet', '')
                    ),
                    description="Pipeline中存在模型训练操作，但缺少模型评估操作",
                    severity=SeverityLevel.HIGH,
                    affected_nodes=[getattr(last_training, 'node_id', 'unknown')],
                    suggestion="添加模型评估步骤，如score()、accuracy_score()、classification_report()等"
                )
                detected_smells.append(smell)
                self.logger.info(f"检测到缺少评估: at line {getattr(last_training, 'line_number', 0)}")
        
        return detected_smells


class ModuleOrderViolationDetector(SmellDetector):
    """模块顺序违反检测器
    
    检测模块顺序不符合预期的问题。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.logger.info("ModuleOrderViolationDetector初始化完成")
    
    def detect(self, pipeline_graph: Any, module_sequence: List[Any]) -> List[SmellInstance]:
        """检测模块顺序违反问题"""
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        if not nodes:
            return detected_smells
        
        # 检查特征选择是否在标准化之后
        feature_selection_nodes = []
        scaler_nodes = []
        
        for node in nodes:
            api_name = getattr(node, 'api_name', '')
            if any(op in api_name for op in ['SelectKBest', 'SelectFromModel', 'RFE', 'VarianceThreshold']):
                feature_selection_nodes.append(node)
            if any(op in api_name for op in ['StandardScaler', 'MinMaxScaler', 'RobustScaler', 'Normalizer']):
                scaler_nodes.append(node)
        
        if feature_selection_nodes and scaler_nodes:
            # 检查是否有标准化在特征选择之前
            for scaler_node in scaler_nodes:
                scaler_line = getattr(scaler_node, 'line_number', 0)
                for fs_node in feature_selection_nodes:
                    fs_line = getattr(fs_node, 'line_number', 0)
                    if scaler_line < fs_line:
                        file_path = getattr(pipeline_graph, 'file_path', 'unknown')
                        
                        smell = self.create_smell_instance(
                            smell_type='MODULE_ORDER_VIOLATION',
                            location=LocationInfo(
                                file_path=file_path,
                                line_number=fs_line,
                                code_snippet=getattr(fs_node, 'code_snippet', '')
                            ),
                            description="特征选择操作在标准化之后执行，可能不是最优顺序",
                            severity=SeverityLevel.MEDIUM,
                            affected_nodes=[getattr(fs_node, 'node_id', 'unknown')],
                            suggestion="考虑将特征选择移到标准化之前，减少不必要的计算"
                        )
                        detected_smells.append(smell)
                        self.logger.info(f"检测到模块顺序违反: at line {fs_line}")
                        break
        
        return detected_smells
