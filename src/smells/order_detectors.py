"""
顺序类Smell检测器模块

提供针对Pipeline顺序问题的检测器，包括数据泄露、缺少评估和模块顺序违反。
所有检测器都继承自SmellDetector基类，实现顺序相关的检测逻辑。
"""

from typing import Any, List

from src.core.modules import ModuleBoundaryDetector, ModuleType, OrderViolation
from src.core.pipeline import PipelineGraph, PipelineNode
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
            'Normalizer.fit'
        ]
        self.logger.info("DataLeakageDetector初始化完成")
    
    def detect(self, pipeline_graph: PipelineGraph, module_sequence: List[ModuleType]) -> List[SmellInstance]:
        """检测Pipeline中的数据泄露问题
        
        遍历Pipeline节点，查找StandardScaler.fit、MinMaxScaler.fit等操作，
        检查这些操作的line_number是否小于train_test_split的line_number。
        若在之前则生成SmellInstance。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序
            
        Returns:
            检测到的Smell实例列表，每个实例代表一处数据泄露问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells
        
        # 查找所有train_test_split节点
        train_test_split_nodes = [
            node for node in nodes 
            if 'train_test_split' in node.api_name
        ]
        
        # 查找所有进行fit操作的节点
        fit_operation_nodes = [
            node for node in nodes 
            if self._is_fit_operation(node.api_name)
        ]
        
        self.logger.debug(f"找到 {len(train_test_split_nodes)} 个train_test_split节点")
        self.logger.debug(f"找到 {len(fit_operation_nodes)} 个fit操作节点")
        
        # 检查每个fit操作是否在train_test_split之前
        for fit_node in fit_operation_nodes:
            for split_node in train_test_split_nodes:
                if fit_node.line_number < split_node.line_number:
                    # 发现数据泄露
                    smell_instance = self._create_data_leakage_smell(
                        fit_node=fit_node,
                        split_node=split_node
                    )
                    detected_smells.append(smell_instance)
                    self.logger.warning(
                        f"检测到数据泄露: {fit_node.api_name} 在第 {fit_node.line_number} 行, "
                        f"位于 train_test_split (第 {split_node.line_number} 行) 之前"
                    )
        
        self.logger.info(f"DataLeakage检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells
    
    def _is_fit_operation(self, api_name: str) -> bool:
        """判断API名称是否为属于数据泄露检测范围的fit操作
        
        Args:
            api_name: API名称
            
        Returns:
            如果是需要进行数据泄露检测的fit操作则返回True，否则返回False
        """
        for operation in self.fit_operations:
            if operation in api_name:
                return True
        return False
    
    def _create_data_leakage_smell(self, fit_node: PipelineNode, 
                                   split_node: PipelineNode) -> SmellInstance:
        """创建数据泄露的Smell实例
        
        Args:
            fit_node: 进行fit操作的节点
            split_node: train_test_split节点
            
        Returns:
            SmellInstance对象
        """
        location = LocationInfo(
            file_path=fit_node.location,
            line_number=fit_node.line_number,
            code_snippet=fit_node.code_snippet
        )
        
        description = (
            f"检测到数据泄露: {fit_node.api_name} 在 train_test_split 之前执行。"
            f"该操作会在整个数据集上计算统计信息，导致测试集信息泄露到训练集中，"
            f"使模型评估过于乐观，实际部署性能下降。"
        )
        
        suggestion = (
            f"建议在第 {split_node.line_number} 行的 train_test_split 之后执行 {fit_node.api_name}。"
            f"正确的做法是：先对训练集调用fit，然后对训练集和测试集分别调用transform。"
        )
        
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.CRITICAL.value,
            affected_nodes=[fit_node.node_id],
            suggestion=suggestion
        )
    
    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的Pipeline节点列表
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按line_number升序排序的PipelineNode列表
        """
        nodes_data = []
        
        for node_id in pipeline_graph.graph.nodes():
            node_data = pipeline_graph.graph.nodes[node_id]
            
            # 从图节点数据中恢复PipelineNode
            pipeline_node = PipelineNode(
                node_id=node_id,
                operation_type=node_data.get('operation_type'),
                api_name=node_data.get('api_name', ''),
                inputs=node_data.get('inputs', []),
                outputs=node_data.get('outputs', []),
                line_number=node_data.get('line_number', 0),
                code_snippet=node_data.get('code_snippet', ''),
                location=node_data.get('location', ''),
                attributes=node_data.get('attributes', {})
            )
            nodes_data.append(pipeline_node)
        
        # 按行号升序排序
        sorted_nodes = sorted(nodes_data, key=lambda x: x.line_number)
        return sorted_nodes


class MissingEvaluationDetector(SmellDetector):
    """缺少模型评估检测器
    
    检测Pipeline中是否存在模型训练但缺少模型评估的情况。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        # 定义模型训练操作列表
        self.training_operations = ['fit', 'train']
        # 定义模型评估操作列表
        self.evaluation_operations = [
            'score', 'evaluate', 'cross_val_score', 
            'accuracy_score', 'f1_score', 'precision_score', 
            'recall_score', 'roc_auc_score', 'mean_squared_error',
            'r2_score', 'confusion_matrix'
        ]
        self.logger.info("MissingEvaluationDetector初始化完成")
    
    def detect(self, pipeline_graph: PipelineGraph, 
               module_sequence: List[ModuleType]) -> List[SmellInstance]:
        """检测Pipeline中缺少模型评估的问题
        
        检查Pipeline末尾是否存在模型评估操作（predict、score、evaluate、cross_val_score）。
        若存在训练操作但无评估操作则生成SmellInstance。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序
            
        Returns:
            检测到的Smell实例列表，每个实例代表一处缺少评估的问题
        """
        detected_smells = []
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        if not nodes:
            self.logger.debug("Pipeline节点列表为空，跳过检测")
            return detected_smells
        
        # 查找所有训练操作节点
        training_nodes = [
            node for node in nodes 
            if any(op in node.api_name for op in self.training_operations)
        ]
        
        # 查找所有评估操作节点
        evaluation_nodes = [
            node for node in nodes 
            if any(op in node.api_name for op in self.evaluation_operations)
        ]
        
        self.logger.debug(f"找到 {len(training_nodes)} 个训练操作节点")
        self.logger.debug(f"找到 {len(evaluation_nodes)} 个评估操作节点")
        
        # 如果存在训练操作但不存在评估操作，则缺少评估
        if len(training_nodes) > 0 and len(evaluation_nodes) == 0:
            # 获取最后一个训练节点作为问题位置
            last_training_node = max(training_nodes, key=lambda x: x.line_number)
            
            smell_instance = self._create_missing_evaluation_smell(
                training_node=last_training_node,
                total_training_nodes=len(training_nodes)
            )
            detected_smells.append(smell_instance)
            self.logger.warning(
                f"检测到缺少模型评估: Pipeline中有 {len(training_nodes)} 个训练操作，"
                f"但没有找到评估操作"
            )
        
        # 检查评估是否在所有训练之前（反向顺序）
        elif training_nodes and evaluation_nodes:
            last_training_line = max(node.line_number for node in training_nodes)
            first_evaluation_line = min(node.line_number for node in evaluation_nodes)
            
            if first_evaluation_line < last_training_line:
                # 存在评估操作，但在所有训练之前（可能是误检测或其他逻辑）
                self.logger.debug(
                    f"发现评估操作在第 {first_evaluation_line} 行, "
                    f"训练操作在第 {last_training_line} 行"
                )
        
        self.logger.info(f"MissingEvaluation检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells
    
    def _create_missing_evaluation_smell(self, training_node: PipelineNode,
                                        total_training_nodes: int) -> SmellInstance:
        """创建缺少模型评估的Smell实例
        
        Args:
            training_node: 训练操作节点
            total_training_nodes: 训练操作的总数
            
        Returns:
            SmellInstance对象
        """
        location = LocationInfo(
            file_path=training_node.location,
            line_number=training_node.line_number,
            code_snippet=training_node.code_snippet
        )
        
        description = (
            f"Pipeline中存在 {total_training_nodes} 个模型训练操作，"
            f"但缺少模型评估操作。存在 {training_node.api_name} 等训练步骤，"
            f"但没有 score()、predict() + 评估指标计算、cross_val_score() 等评估步骤。"
            f"这导致无法评估模型性能，模型训练结果缺乏依据。"
        )
        
        suggestion = (
            "建议在模型训练后添加评估步骤。推荐方法："
            "1. 使用 model.score(X_test, y_test) 进行快速评估；"
            "2. 使用 predict() 预测后计算 accuracy_score、f1_score 等指标；"
            "3. 使用 cross_val_score() 进行交叉验证评估。"
        )
        
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.HIGH.value,
            affected_nodes=[training_node.node_id],
            suggestion=suggestion
        )
    
    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的Pipeline节点列表
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按line_number升序排序的PipelineNode列表
        """
        nodes_data = []
        
        for node_id in pipeline_graph.graph.nodes():
            node_data = pipeline_graph.graph.nodes[node_id]
            
            pipeline_node = PipelineNode(
                node_id=node_id,
                operation_type=node_data.get('operation_type'),
                api_name=node_data.get('api_name', ''),
                inputs=node_data.get('inputs', []),
                outputs=node_data.get('outputs', []),
                line_number=node_data.get('line_number', 0),
                code_snippet=node_data.get('code_snippet', ''),
                location=node_data.get('location', ''),
                attributes=node_data.get('attributes', {})
            )
            nodes_data.append(pipeline_node)
        
        sorted_nodes = sorted(nodes_data, key=lambda x: x.line_number)
        return sorted_nodes


class ModuleOrderViolationDetector(SmellDetector):
    """模块顺序违反检测器
    
    检测Pipeline中模块的执行顺序是否符合常规的数据处理流程。
    """
    
    def __init__(self):
        """初始化检测器"""
        super().__init__()
        self.module_boundary_detector = ModuleBoundaryDetector()
        self.logger.info("ModuleOrderViolationDetector初始化完成")
    
    def detect(self, pipeline_graph: PipelineGraph, 
               module_sequence: List[ModuleType]) -> List[SmellInstance]:
        """检测Pipeline中的模块顺序违反问题
        
        接收module_sequence，调用ModuleBoundaryDetector.validate_order()，
        将返回的OrderViolation列表转换为SmellInstance。
        
        Args:
            pipeline_graph: Pipeline图对象，包含节点和边信息
            module_sequence: 模块类型序列，表示Pipeline中模块的执行顺序
            
        Returns:
            检测到的Smell实例列表，每个实例代表一处模块顺序违反的问题
        """
        detected_smells = []
        
        if not module_sequence:
            self.logger.debug("模块序列为空，跳过检测")
            return detected_smells
        
        # 调用ModuleBoundaryDetector验证模块顺序
        validation_result = self.module_boundary_detector.validate_order(module_sequence)
        
        if validation_result.is_valid:
            self.logger.info("模块顺序验证通过")
            return detected_smells
        
        # 获取Pipeline节点以获取位置信息
        nodes = self._get_sorted_nodes(pipeline_graph)
        
        # 将OrderViolation转换为SmellInstance
        for violation in validation_result.violations:
            smell_instance = self._create_order_violation_smell(
                violation=violation,
                nodes=nodes
            )
            detected_smells.append(smell_instance)
            self.logger.warning(
                f"检测到模块顺序违反: 索引 {violation.index}, "
                f"当前模块 {violation.current_module.value}, "
                f"期望模块 {violation.expected_module.value}"
            )
        
        self.logger.info(f"ModuleOrderViolation检测完成，发现 {len(detected_smells)} 个问题")
        return detected_smells
    
    def _create_order_violation_smell(self, violation: OrderViolation,
                                     nodes: List[PipelineNode]) -> SmellInstance:
        """创建模块顺序违反的Smell实例
        
        Args:
            violation: OrderViolation对象，包含违规位置和模块类型
            nodes: Pipeline节点列表，用于获取位置信息
            
        Returns:
            SmellInstance对象
        """
        # 获取违规索引处的节点
        location_node = None
        if violation.index < len(nodes):
            location_node = nodes[violation.index]
        
        if location_node:
            location = LocationInfo(
                file_path=location_node.location,
                line_number=location_node.line_number,
                code_snippet=location_node.code_snippet
            )
            affected_node = location_node.node_id
            current_module_name = location_node.api_name
        else:
            # 如果无法获取节点信息，使用默认值
            location = LocationInfo(
                file_path="unknown",
                line_number=violation.index,
                code_snippet=""
            )
            affected_node = f"node_at_index_{violation.index}"
            current_module_name = violation.current_module.value
        
        description = (
            f"模块顺序违反预期: 在Pipeline索引 {violation.index} 处，"
            f"当前模块类型为 {current_module_name} ({violation.current_module.value})，"
            f"但期望的模块类型为 {violation.expected_module.value}。"
            f"这种顺序违反了常规的数据处理流程，可能导致运行时错误或产生错误的处理结果。"
        )
        
        suggestion = (
            f"建议调整模块顺序，确保 Pipeline 遵循以下流程："
            f"1. 数据获取 (DATA_ACQUISITION) -> "
            f"2. 数据清洗 (DATA_CLEANING) -> "
            f"3. 特征工程 (FEATURE_ENGINEERING) -> "
            f"4. 模型操作 (MODEL_OPERATION)。"
            f"当前应将 {current_module_name} 相关操作移动到正确的阶段。"
        )
        
        return self.create_smell_instance(
            location=location,
            description=description,
            severity=SeverityLevel.MEDIUM.value,
            affected_nodes=[affected_node],
            suggestion=suggestion
        )
    
    def _get_sorted_nodes(self, pipeline_graph: PipelineGraph) -> List[PipelineNode]:
        """获取按行号排序的Pipeline节点列表
        
        Args:
            pipeline_graph: Pipeline图对象
            
        Returns:
            按line_number升序排序的PipelineNode列表
        """
        nodes_data = []
        
        for node_id in pipeline_graph.graph.nodes():
            node_data = pipeline_graph.graph.nodes[node_id]
            
            pipeline_node = PipelineNode(
                node_id=node_id,
                operation_type=node_data.get('operation_type'),
                api_name=node_data.get('api_name', ''),
                inputs=node_data.get('inputs', []),
                outputs=node_data.get('outputs', []),
                line_number=node_data.get('line_number', 0),
                code_snippet=node_data.get('code_snippet', ''),
                location=node_data.get('location', ''),
                attributes=node_data.get('attributes', {})
            )
            nodes_data.append(pipeline_node)
        
        sorted_nodes = sorted(nodes_data, key=lambda x: x.line_number)
        return sorted_nodes
