"""
评估指标计算模块

提供Precision、Recall、F1-score等标准评估指标的计算功能。
支持多类别、多标签的评估场景。
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

import numpy as np

from src.evaluation.matcher import MatchingResult


@dataclass
class ConfusionMatrix:
    """混淆矩阵数据类"""
    true_positives: int  # 真阳性
    false_positives: int  # 假阳性
    true_negatives: int  # 真阴性
    false_negatives: int  # 假阴性
    
    def precision(self) -> float:
        """计算精确率
        
        Returns:
            精确率值，范围[0, 1]
        """
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)
    
    def recall(self) -> float:
        """计算召回率
        
        Returns:
            召回率值，范围[0, 1]
        """
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)
    
    def f1_score(self) -> float:
        """计算F1分数
        
        Returns:
            F1分数值，范围[0, 1]
        """
        p = self.precision()
        r = self.recall()
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)
    
    def accuracy(self) -> float:
        """计算准确率
        
        Returns:
            准确率值，范围[0, 1]
        """
        total = self.true_positives + self.false_positives + \
                self.true_negatives + self.false_negatives
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total
    
    def specificity(self) -> float:
        """计算特异性
        
        Returns:
            特异性值，范围[0, 1]
        """
        if self.true_negatives + self.false_positives == 0:
            return 0.0
        return self.true_negatives / (self.true_negatives + self.false_positives)


@dataclass
class MetricsResult:
    """评估指标结果数据类"""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    confusion_matrix: ConfusionMatrix
    
    # 额外的统计信息
    total_predictions: int
    total_ground_truth: int
    true_positives_count: int
    false_positives_count: int
    false_negatives_count: int
    
    def to_dict(self) -> Dict:
        """转换为字典格式
        
        Returns:
            包含所有指标的字典
        """
        return {
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'accuracy': self.accuracy,
            'total_predictions': self.total_predictions,
            'total_ground_truth': self.total_ground_truth,
            'true_positives': self.true_positives_count,
            'false_positives': self.false_positives_count,
            'false_negatives': self.false_negatives_count
        }


class MetricsCalculator:
    """评估指标计算器
    
    提供多种评估指标的计算功能，支持单类别和多类别评估。
    """
    
    @staticmethod
    def calculate_binary_metrics(predictions: Set[str], 
                                 ground_truth: Set[str],
                                 total_possible: int = None) -> MetricsResult:
        """计算二分类指标
        
        Args:
            predictions: 预测的Smell实例ID集合
            ground_truth: 真实的Smell实例ID集合
            total_possible: 可能的总实例数（用于计算TN）
            
        Returns:
            MetricsResult对象
        """
        tp = len(predictions & ground_truth)  # 交集
        fp = len(predictions - ground_truth)  # 预测有但实际没有
        fn = len(ground_truth - predictions)  # 实际有但预测没有
        
        # 如果提供了total_possible，计算TN
        if total_possible is not None:
            tn = total_possible - tp - fp - fn
        else:
            tn = 0
        
        cm = ConfusionMatrix(
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn
        )
        
        return MetricsResult(
            precision=cm.precision(),
            recall=cm.recall(),
            f1_score=cm.f1_score(),
            accuracy=cm.accuracy(),
            confusion_matrix=cm,
            total_predictions=len(predictions),
            total_ground_truth=len(ground_truth),
            true_positives_count=tp,
            false_positives_count=fp,
            false_negatives_count=fn
        )
    
    @staticmethod
    def from_matching_result(matching_result: MatchingResult) -> MetricsResult:
        """根据匹配结果计算 Precision / Recall / F1（支持行容差等模糊匹配）。"""
        tp = len(matching_result.matches)
        fp = len(matching_result.unmatched_predictions)
        fn = len(matching_result.unmatched_ground_truth)
        cm = ConfusionMatrix(
            true_positives=tp,
            false_positives=fp,
            true_negatives=0,
            false_negatives=fn
        )
        return MetricsResult(
            precision=cm.precision(),
            recall=cm.recall(),
            f1_score=cm.f1_score(),
            accuracy=cm.accuracy(),
            confusion_matrix=cm,
            total_predictions=tp + fp,
            total_ground_truth=tp + fn,
            true_positives_count=tp,
            false_positives_count=fp,
            false_negatives_count=fn
        )
    
    @staticmethod
    def calculate_multiclass_metrics(predictions_by_class: Dict[str, Set[str]],
                                     ground_truth_by_class: Dict[str, Set[str]],
                                     average: str = 'macro') -> Dict[str, MetricsResult]:
        """计算多类别指标
        
        Args:
            predictions_by_class: 按类别分组的预测集合
            ground_truth_by_class: 按类别分组的真实集合
            average: 平均方式，'macro'（宏平均）或'micro'（微平均）
            
        Returns:
            每个类别的MetricsResult字典，包含'overall'键表示总体指标
        """
        results = {}
        
        # 计算每个类别的指标
        all_classes = set(predictions_by_class.keys()) | set(ground_truth_by_class.keys())
        
        for class_name in all_classes:
            preds = predictions_by_class.get(class_name, set())
            gt = ground_truth_by_class.get(class_name, set())
            
            results[class_name] = MetricsCalculator.calculate_binary_metrics(preds, gt)
        
        # 计算总体指标
        if average == 'macro':
            # 宏平均：每个类别权重相同
            avg_precision = np.mean([r.precision for r in results.values()])
            avg_recall = np.mean([r.recall for r in results.values()])
            avg_f1 = np.mean([r.f1_score for r in results.values()])
            
            total_tp = sum(r.true_positives_count for r in results.values())
            total_fp = sum(r.false_positives_count for r in results.values())
            total_fn = sum(r.false_negatives_count for r in results.values())
            
        else:  # micro
            # 微平均：所有实例权重相同
            total_tp = sum(r.true_positives_count for r in results.values())
            total_fp = sum(r.false_positives_count for r in results.values())
            total_fn = sum(r.false_negatives_count for r in results.values())
            
            cm = ConfusionMatrix(
                true_positives=total_tp,
                false_positives=total_fp,
                true_negatives=0,
                false_negatives=total_fn
            )
            
            avg_precision = cm.precision()
            avg_recall = cm.recall()
            avg_f1 = cm.f1_score()
        
        # 创建总体结果
        overall_cm = ConfusionMatrix(
            true_positives=total_tp,
            false_positives=total_fp,
            true_negatives=0,
            false_negatives=total_fn
        )
        
        results['overall'] = MetricsResult(
            precision=avg_precision,
            recall=avg_recall,
            f1_score=avg_f1,
            accuracy=0.0,  # 多类别场景下accuracy定义不同
            confusion_matrix=overall_cm,
            total_predictions=sum(r.total_predictions for r in results.values() if r != results.get('overall')),
            total_ground_truth=sum(r.total_ground_truth for r in results.values() if r != results.get('overall')),
            true_positives_count=total_tp,
            false_positives_count=total_fp,
            false_negatives_count=total_fn
        )
        
        return results
    
    @staticmethod
    def calculate_per_smell_metrics(predictions: List[Dict],
                                    ground_truth: List[Dict]) -> Dict[str, MetricsResult]:
        """按Smell类型计算指标
        
        Args:
            predictions: 预测的Smell列表，每个元素包含'smell_type'和'id'
            ground_truth: 真实的Smell列表，每个元素包含'smell_type'和'id'
            
        Returns:
            每个Smell类型的MetricsResult字典
        """
        # 按smell_type分组
        pred_by_type = {}
        gt_by_type = {}
        
        for pred in predictions:
            smell_type = pred.get('smell_type', 'UNKNOWN')
            smell_id = pred.get('id', '')
            if smell_type not in pred_by_type:
                pred_by_type[smell_type] = set()
            pred_by_type[smell_type].add(smell_id)
        
        for gt in ground_truth:
            smell_type = gt.get('smell_type', 'UNKNOWN')
            smell_id = gt.get('id', '')
            if smell_type not in gt_by_type:
                gt_by_type[smell_type] = set()
            gt_by_type[smell_type].add(smell_id)
        
        return MetricsCalculator.calculate_multiclass_metrics(
            pred_by_type, gt_by_type, average='macro'
        )


class RankingMetrics:
    """排序评估指标
    
    用于评估检测结果的排序质量（按严重性或置信度排序）。
    """
    
    @staticmethod
    def mean_average_precision(predictions: List[Tuple[str, float]],
                               ground_truth: Set[str]) -> float:
        """计算平均精度均值（MAP）
        
        Args:
            predictions: 预测列表，每个元素为(smell_id, confidence_score)
            ground_truth: 真实Smell ID集合
            
        Returns:
            MAP值，范围[0, 1]
        """
        if not ground_truth:
            return 0.0
        
        # 按置信度降序排序
        sorted_preds = sorted(predictions, key=lambda x: x[1], reverse=True)
        
        num_hits = 0
        sum_precisions = 0.0
        
        for i, (smell_id, _) in enumerate(sorted_preds):
            if smell_id in ground_truth:
                num_hits += 1
                precision_at_k = num_hits / (i + 1)
                sum_precisions += precision_at_k
        
        if num_hits == 0:
            return 0.0
        
        return sum_precisions / len(ground_truth)
    
    @staticmethod
    def precision_at_k(predictions: List[str],
                      ground_truth: Set[str],
                      k: int) -> float:
        """计算P@K（前K个预测的精确率）
        
        Args:
            predictions: 预测列表（已排序）
            ground_truth: 真实Smell ID集合
            k: 截断位置
            
        Returns:
            P@K值，范围[0, 1]
        """
        if k <= 0 or not predictions:
            return 0.0
        
        top_k = predictions[:k]
        hits = sum(1 for pred in top_k if pred in ground_truth)
        
        return hits / k
    
    @staticmethod
    def recall_at_k(predictions: List[str],
                   ground_truth: Set[str],
                   k: int) -> float:
        """计算R@K（前K个预测的召回率）
        
        Args:
            predictions: 预测列表（已排序）
            ground_truth: 真实Smell ID集合
            k: 截断位置
            
        Returns:
            R@K值，范围[0, 1]
        """
        if k <= 0 or not predictions or not ground_truth:
            return 0.0
        
        top_k = predictions[:k]
        hits = sum(1 for pred in top_k if pred in ground_truth)
        
        return hits / len(ground_truth)


def calculate_cohen_kappa(annotator1: List[str],
                         annotator2: List[str]) -> float:
    """计算Cohen's Kappa系数（标注一致性）
    
    Args:
        annotator1: 标注者1的标注列表
        annotator2: 标注者2的标注列表
        
    Returns:
        Kappa系数，范围[-1, 1]，>0.7表示一致性良好
    """
    if len(annotator1) != len(annotator2):
        raise ValueError("两个标注列表长度必须相同")
    
    n = len(annotator1)
    if n == 0:
        return 0.0
    
    # 计算观察一致性
    agreements = sum(1 for a, b in zip(annotator1, annotator2) if a == b)
    po = agreements / n
    
    # 计算期望一致性
    categories = set(annotator1 + annotator2)
    pe = 0.0
    
    for category in categories:
        p1 = annotator1.count(category) / n
        p2 = annotator2.count(category) / n
        pe += p1 * p2
    
    # 计算Kappa
    if pe == 1.0:
        return 1.0
    
    kappa = (po - pe) / (1 - pe)
    return kappa
