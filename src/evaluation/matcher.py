"""
Ground Truth匹配模块

提供预测结果与Ground Truth的匹配算法，支持精确匹配和模糊匹配。
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def _canonical_file_path(file_path: str) -> str:
    """将路径规范为绝对路径字符串，便于跨平台一致比较。"""
    if not file_path:
        return ''
    p = Path(file_path).expanduser()
    try:
        return str(p.resolve())
    except OSError:
        return str(p)


def _paths_equivalent(a: str, b: str) -> bool:
    """判断两处路径是否指向同一文件（兼容 Windows 大小写/分隔符差异）。"""
    if not a or not b:
        return a == b
    ca, cb = _canonical_file_path(a), _canonical_file_path(b)
    if ca == cb:
        return True
    return os.path.normcase(ca) == os.path.normcase(cb)


class MatchStrategy(Enum):
    """匹配策略枚举"""
    EXACT = "exact"  # 精确匹配（文件+行号+smell类型）
    LINE_RANGE = "line_range"  # 行范围匹配（允许±N行误差）
    SEMANTIC = "semantic"  # 语义匹配（基于affected_nodes）


@dataclass
class SmellMatch:
    """Smell匹配结果"""
    prediction_id: str
    ground_truth_id: str
    smell_type: str
    match_score: float  # 匹配置信度，范围[0, 1]
    match_strategy: MatchStrategy


@dataclass
class MatchingResult:
    """匹配结果数据类"""
    matches: List[SmellMatch]  # 成功匹配的列表
    unmatched_predictions: List[Dict]  # 未匹配的预测（假阳性）
    unmatched_ground_truth: List[Dict]  # 未匹配的真实标注（假阴性）
    
    def get_true_positives(self) -> List[SmellMatch]:
        """获取真阳性（成功匹配）"""
        return self.matches
    
    def get_false_positives(self) -> List[Dict]:
        """获取假阳性（预测但不在GT中）"""
        return self.unmatched_predictions
    
    def get_false_negatives(self) -> List[Dict]:
        """获取假阴性（GT中有但未预测）"""
        return self.unmatched_ground_truth
    
    def get_statistics(self) -> Dict:
        """获取匹配统计信息"""
        return {
            'total_matches': len(self.matches),
            'total_predictions': len(self.matches) + len(self.unmatched_predictions),
            'total_ground_truth': len(self.matches) + len(self.unmatched_ground_truth),
            'precision': len(self.matches) / (len(self.matches) + len(self.unmatched_predictions)) 
                        if (len(self.matches) + len(self.unmatched_predictions)) > 0 else 0.0,
            'recall': len(self.matches) / (len(self.matches) + len(self.unmatched_ground_truth))
                     if (len(self.matches) + len(self.unmatched_ground_truth)) > 0 else 0.0
        }


class GroundTruthMatcher:
    """Ground Truth匹配器
    
    负责将检测结果与Ground Truth进行匹配，支持多种匹配策略。
    """
    
    def __init__(self, strategy: MatchStrategy = MatchStrategy.LINE_RANGE,
                 line_tolerance: int = 2):
        """初始化匹配器
        
        Args:
            strategy: 匹配策略
            line_tolerance: 行号容差（仅用于LINE_RANGE策略）
        """
        self.strategy = strategy
        self.line_tolerance = line_tolerance
    
    def match(self, predictions: List[Dict], ground_truth: List[Dict]) -> MatchingResult:
        """执行匹配
        
        Args:
            predictions: 预测的Smell列表，每个元素包含:
                - id: 唯一标识
                - smell_type: Smell类型
                - file_path: 文件路径
                - line_number: 行号
                - affected_nodes: 影响的节点列表（可选）
            ground_truth: Ground Truth Smell列表，格式同上
            
        Returns:
            MatchingResult对象
        """
        if self.strategy == MatchStrategy.EXACT:
            return self._exact_match(predictions, ground_truth)
        elif self.strategy == MatchStrategy.LINE_RANGE:
            return self._line_range_match(predictions, ground_truth)
        elif self.strategy == MatchStrategy.SEMANTIC:
            return self._semantic_match(predictions, ground_truth)
        else:
            raise ValueError(f"不支持的匹配策略: {self.strategy}")
    
    def _exact_match(self, predictions: List[Dict], ground_truth: List[Dict]) -> MatchingResult:
        """精确匹配：文件路径、行号、Smell类型必须完全一致
        
        Args:
            predictions: 预测列表
            ground_truth: 真实标注列表
            
        Returns:
            MatchingResult对象
        """
        matches = []
        matched_pred_ids = set()
        matched_gt_ids = set()
        
        # 为GT建立索引
        gt_index = {}
        for gt in ground_truth:
            key = self._create_exact_key(gt)
            if key not in gt_index:
                gt_index[key] = []
            gt_index[key].append(gt)
        
        # 匹配预测
        for pred in predictions:
            key = self._create_exact_key(pred)
            
            if key in gt_index and gt_index[key]:
                # 找到匹配
                gt_match = gt_index[key].pop(0)
                
                matches.append(SmellMatch(
                    prediction_id=pred['id'],
                    ground_truth_id=gt_match['id'],
                    smell_type=pred['smell_type'],
                    match_score=1.0,
                    match_strategy=MatchStrategy.EXACT
                ))
                
                matched_pred_ids.add(pred['id'])
                matched_gt_ids.add(gt_match['id'])
        
        # 收集未匹配的
        unmatched_preds = [p for p in predictions if p['id'] not in matched_pred_ids]
        unmatched_gts = [g for g in ground_truth if g['id'] not in matched_gt_ids]
        
        return MatchingResult(
            matches=matches,
            unmatched_predictions=unmatched_preds,
            unmatched_ground_truth=unmatched_gts
        )
    
    def _line_range_match(self, predictions: List[Dict], ground_truth: List[Dict]) -> MatchingResult:
        """行范围匹配：允许行号有一定误差
        
        Args:
            predictions: 预测列表
            ground_truth: 真实标注列表
            
        Returns:
            MatchingResult对象
        """
        matches = []
        matched_pred_ids = set()
        matched_gt_ids = set()
        
        # 为每个预测找最佳匹配
        for pred in predictions:
            best_match = None
            best_score = 0.0
            
            for gt in ground_truth:
                if gt['id'] in matched_gt_ids:
                    continue
                
                # 检查文件路径和Smell类型
                if (pred['file_path'] != gt['file_path'] or
                    pred['smell_type'] != gt['smell_type']):
                    continue
                
                # 计算行号距离
                line_distance = abs(pred['line_number'] - gt['line_number'])
                
                if line_distance <= self.line_tolerance:
                    # 计算匹配分数（距离越小分数越高）
                    score = 1.0 - (line_distance / (self.line_tolerance + 1))
                    
                    if score > best_score:
                        best_score = score
                        best_match = gt
            
            # 如果找到匹配
            if best_match is not None:
                matches.append(SmellMatch(
                    prediction_id=pred['id'],
                    ground_truth_id=best_match['id'],
                    smell_type=pred['smell_type'],
                    match_score=best_score,
                    match_strategy=MatchStrategy.LINE_RANGE
                ))
                
                matched_pred_ids.add(pred['id'])
                matched_gt_ids.add(best_match['id'])
        
        # 收集未匹配的
        unmatched_preds = [p for p in predictions if p['id'] not in matched_pred_ids]
        unmatched_gts = [g for g in ground_truth if g['id'] not in matched_gt_ids]
        
        return MatchingResult(
            matches=matches,
            unmatched_predictions=unmatched_preds,
            unmatched_ground_truth=unmatched_gts
        )
    
    def _semantic_match(self, predictions: List[Dict], ground_truth: List[Dict]) -> MatchingResult:
        """语义匹配：基于affected_nodes的重叠度
        
        Args:
            predictions: 预测列表
            ground_truth: 真实标注列表
            
        Returns:
            MatchingResult对象
        """
        matches = []
        matched_pred_ids = set()
        matched_gt_ids = set()
        
        # 为每个预测找最佳匹配
        for pred in predictions:
            best_match = None
            best_score = 0.0
            
            pred_nodes = set(pred.get('affected_nodes', []))
            
            for gt in ground_truth:
                if gt['id'] in matched_gt_ids:
                    continue
                
                # 检查文件路径和Smell类型
                if (not _paths_equivalent(pred['file_path'], gt['file_path']) or
                        pred['smell_type'] != gt['smell_type']):
                    continue

                gt_nodes = set(gt.get('affected_nodes', []))
                
                # 计算Jaccard相似度
                if pred_nodes or gt_nodes:
                    intersection = len(pred_nodes & gt_nodes)
                    union = len(pred_nodes | gt_nodes)
                    
                    if union > 0:
                        score = intersection / union
                        
                        if score > best_score and score >= 0.5:  # 至少50%重叠
                            best_score = score
                            best_match = gt
            
            # 如果找到匹配
            if best_match is not None:
                matches.append(SmellMatch(
                    prediction_id=pred['id'],
                    ground_truth_id=best_match['id'],
                    smell_type=pred['smell_type'],
                    match_score=best_score,
                    match_strategy=MatchStrategy.SEMANTIC
                ))
                
                matched_pred_ids.add(pred['id'])
                matched_gt_ids.add(best_match['id'])
        
        # 收集未匹配的
        unmatched_preds = [p for p in predictions if p['id'] not in matched_pred_ids]
        unmatched_gts = [g for g in ground_truth if g['id'] not in matched_gt_ids]
        
        return MatchingResult(
            matches=matches,
            unmatched_predictions=unmatched_preds,
            unmatched_ground_truth=unmatched_gts
        )
    
    def _create_exact_key(self, smell: Dict) -> Tuple:
        """创建精确匹配的键
        
        Args:
            smell: Smell字典
            
        Returns:
            用于精确匹配的元组键
        """
        return (
            _canonical_file_path(smell['file_path']),
            smell['line_number'],
            smell['smell_type'],
        )


class BatchMatcher:
    """批量匹配器
    
    用于批量处理多个文件的匹配任务。
    """
    
    def __init__(self, matcher: GroundTruthMatcher):
        """初始化批量匹配器
        
        Args:
            matcher: GroundTruthMatcher实例
        """
        self.matcher = matcher
    
    def match_batch(self, predictions_by_file: Dict[str, List[Dict]],
                   ground_truth_by_file: Dict[str, List[Dict]]) -> Dict[str, MatchingResult]:
        """批量匹配多个文件
        
        Args:
            predictions_by_file: 按文件分组的预测字典
            ground_truth_by_file: 按文件分组的Ground Truth字典
            
        Returns:
            每个文件的MatchingResult字典
        """
        results = {}
        
        all_files = set(predictions_by_file.keys()) | set(ground_truth_by_file.keys())
        
        for file_path in all_files:
            preds = predictions_by_file.get(file_path, [])
            gts = ground_truth_by_file.get(file_path, [])
            
            results[file_path] = self.matcher.match(preds, gts)
        
        return results
    
    def aggregate_results(self, results_by_file: Dict[str, MatchingResult]) -> MatchingResult:
        """聚合多个文件的匹配结果
        
        Args:
            results_by_file: 每个文件的MatchingResult字典
            
        Returns:
            聚合后的MatchingResult
        """
        all_matches = []
        all_unmatched_preds = []
        all_unmatched_gts = []
        
        for result in results_by_file.values():
            all_matches.extend(result.matches)
            all_unmatched_preds.extend(result.unmatched_predictions)
            all_unmatched_gts.extend(result.unmatched_ground_truth)
        
        return MatchingResult(
            matches=all_matches,
            unmatched_predictions=all_unmatched_preds,
            unmatched_ground_truth=all_unmatched_gts
        )
