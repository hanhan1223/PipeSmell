"""
评估器模块

提供完整的评估流程，包括数据加载、匹配、指标计算和结果输出。
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.core.logger import Logger
from src.evaluation.matcher import GroundTruthMatcher, MatchStrategy, BatchMatcher
from src.evaluation.metrics import MetricsCalculator, MetricsResult


@dataclass
class EvaluationConfig:
    """评估配置"""
    match_strategy: MatchStrategy = MatchStrategy.LINE_RANGE
    line_tolerance: int = 2
    output_dir: str = "experiments/results"
    save_detailed_results: bool = True
    calculate_per_smell_metrics: bool = True


@dataclass
class EvaluationResult:
    """评估结果数据类"""
    method_name: str  # 方法名称（如"Pipeline-aware"、"Baseline-Keyword"等）
    overall_metrics: MetricsResult  # 总体指标
    per_smell_metrics: Dict[str, MetricsResult]  # 每个Smell类型的指标
    per_file_metrics: Dict[str, MetricsResult]  # 每个文件的指标（可选）
    runtime_ms: float  # 运行时间（毫秒）
    config: EvaluationConfig  # 评估配置
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'method_name': self.method_name,
            'overall_metrics': self.overall_metrics.to_dict(),
            'per_smell_metrics': {
                smell_type: metrics.to_dict()
                for smell_type, metrics in self.per_smell_metrics.items()
            },
            'runtime_ms': self.runtime_ms,
            'config': {
                'match_strategy': self.config.match_strategy.value,
                'line_tolerance': self.config.line_tolerance
            }
        }
    
    def get_summary(self) -> Dict:
        """获取摘要信息"""
        return {
            'method': self.method_name,
            'precision': self.overall_metrics.precision,
            'recall': self.overall_metrics.recall,
            'f1_score': self.overall_metrics.f1_score,
            'total_predictions': self.overall_metrics.total_predictions,
            'total_ground_truth': self.overall_metrics.total_ground_truth,
            'runtime_ms': self.runtime_ms
        }


class Evaluator:
    """评估器
    
    负责执行完整的评估流程，包括：
    1. 加载预测结果和Ground Truth
    2. 执行匹配
    3. 计算评估指标
    4. 保存结果
    """
    
    def __init__(self, config: EvaluationConfig = None):
        """初始化评估器
        
        Args:
            config: 评估配置，如果为None则使用默认配置
        """
        self.config = config or EvaluationConfig()
        self.logger = Logger.setup('Evaluator', 'logs/evaluation.log')
        
        # 创建输出目录
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def evaluate(self, predictions: List[Dict], ground_truth: List[Dict],
                method_name: str = "Unknown") -> EvaluationResult:
        """执行评估
        
        Args:
            predictions: 预测的Smell列表
            ground_truth: Ground Truth Smell列表
            method_name: 方法名称
            
        Returns:
            EvaluationResult对象
        """
        start_time = time.time()
        
        self.logger.info(f"开始评估方法: {method_name}")
        self.logger.info(f"预测数量: {len(predictions)}, Ground Truth数量: {len(ground_truth)}")
        
        # 1. 执行匹配
        matcher = GroundTruthMatcher(
            strategy=self.config.match_strategy,
            line_tolerance=self.config.line_tolerance
        )
        
        matching_result = matcher.match(predictions, ground_truth)
        
        self.logger.info(f"匹配完成: {len(matching_result.matches)} 个成功匹配")
        
        # 2. 计算总体指标
        pred_ids = set(p['id'] for p in predictions)
        gt_ids = set(g['id'] for g in ground_truth)
        
        overall_metrics = MetricsCalculator.calculate_binary_metrics(pred_ids, gt_ids)
        
        # 3. 计算每个Smell类型的指标
        per_smell_metrics = {}
        if self.config.calculate_per_smell_metrics:
            per_smell_metrics = MetricsCalculator.calculate_per_smell_metrics(
                predictions, ground_truth
            )
        
        runtime_ms = (time.time() - start_time) * 1000
        
        result = EvaluationResult(
            method_name=method_name,
            overall_metrics=overall_metrics,
            per_smell_metrics=per_smell_metrics,
            per_file_metrics={},  # 可选
            runtime_ms=runtime_ms,
            config=self.config
        )
        
        self.logger.info(f"评估完成: P={overall_metrics.precision:.3f}, "
                        f"R={overall_metrics.recall:.3f}, "
                        f"F1={overall_metrics.f1_score:.3f}")
        
        # 4. 保存结果
        if self.config.save_detailed_results:
            self._save_results(result, matching_result)
        
        return result
    
    def evaluate_batch(self, predictions_by_file: Dict[str, List[Dict]],
                      ground_truth_by_file: Dict[str, List[Dict]],
                      method_name: str = "Unknown") -> EvaluationResult:
        """批量评估多个文件
        
        Args:
            predictions_by_file: 按文件分组的预测字典
            ground_truth_by_file: 按文件分组的Ground Truth字典
            method_name: 方法名称
            
        Returns:
            EvaluationResult对象
        """
        start_time = time.time()
        
        self.logger.info(f"开始批量评估方法: {method_name}")
        self.logger.info(f"文件数量: {len(set(predictions_by_file.keys()) | set(ground_truth_by_file.keys()))}")
        
        # 1. 批量匹配
        matcher = GroundTruthMatcher(
            strategy=self.config.match_strategy,
            line_tolerance=self.config.line_tolerance
        )
        batch_matcher = BatchMatcher(matcher)
        
        results_by_file = batch_matcher.match_batch(predictions_by_file, ground_truth_by_file)
        
        # 2. 聚合结果
        aggregated_result = batch_matcher.aggregate_results(results_by_file)
        
        # 3. 计算总体指标
        all_predictions = []
        all_ground_truth = []
        
        for preds in predictions_by_file.values():
            all_predictions.extend(preds)
        
        for gts in ground_truth_by_file.values():
            all_ground_truth.extend(gts)
        
        pred_ids = set(p['id'] for p in all_predictions)
        gt_ids = set(g['id'] for g in all_ground_truth)
        
        overall_metrics = MetricsCalculator.calculate_binary_metrics(pred_ids, gt_ids)
        
        # 4. 计算每个Smell类型的指标
        per_smell_metrics = {}
        if self.config.calculate_per_smell_metrics:
            per_smell_metrics = MetricsCalculator.calculate_per_smell_metrics(
                all_predictions, all_ground_truth
            )
        
        # 5. 计算每个文件的指标
        per_file_metrics = {}
        for file_path, file_result in results_by_file.items():
            file_preds = predictions_by_file.get(file_path, [])
            file_gts = ground_truth_by_file.get(file_path, [])
            
            if file_preds or file_gts:
                file_pred_ids = set(p['id'] for p in file_preds)
                file_gt_ids = set(g['id'] for g in file_gts)
                
                per_file_metrics[file_path] = MetricsCalculator.calculate_binary_metrics(
                    file_pred_ids, file_gt_ids
                )
        
        runtime_ms = (time.time() - start_time) * 1000
        
        result = EvaluationResult(
            method_name=method_name,
            overall_metrics=overall_metrics,
            per_smell_metrics=per_smell_metrics,
            per_file_metrics=per_file_metrics,
            runtime_ms=runtime_ms,
            config=self.config
        )
        
        self.logger.info(f"批量评估完成: P={overall_metrics.precision:.3f}, "
                        f"R={overall_metrics.recall:.3f}, "
                        f"F1={overall_metrics.f1_score:.3f}")
        
        # 6. 保存结果
        if self.config.save_detailed_results:
            self._save_results(result, aggregated_result)
        
        return result
    
    def compare_methods(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """比较多个方法的评估结果
        
        Args:
            results: EvaluationResult列表
            
        Returns:
            比较结果字典
        """
        comparison = {
            'methods': [],
            'overall_comparison': {},
            'per_smell_comparison': {}
        }
        
        # 收集所有方法的总体指标
        for result in results:
            comparison['methods'].append({
                'name': result.method_name,
                'precision': result.overall_metrics.precision,
                'recall': result.overall_metrics.recall,
                'f1_score': result.overall_metrics.f1_score,
                'runtime_ms': result.runtime_ms
            })
        
        # 按F1分数排序
        comparison['methods'].sort(key=lambda x: x['f1_score'], reverse=True)
        
        # 找出最佳方法
        if comparison['methods']:
            best_method = comparison['methods'][0]
            comparison['best_method'] = best_method['name']
            comparison['best_f1'] = best_method['f1_score']
        
        # 比较每个Smell类型的性能
        all_smell_types = set()
        for result in results:
            all_smell_types.update(result.per_smell_metrics.keys())
        
        for smell_type in all_smell_types:
            if smell_type == 'overall':
                continue
            
            comparison['per_smell_comparison'][smell_type] = []
            
            for result in results:
                if smell_type in result.per_smell_metrics:
                    metrics = result.per_smell_metrics[smell_type]
                    comparison['per_smell_comparison'][smell_type].append({
                        'method': result.method_name,
                        'precision': metrics.precision,
                        'recall': metrics.recall,
                        'f1_score': metrics.f1_score
                    })
        
        # 保存比较结果
        output_path = Path(self.config.output_dir) / "method_comparison.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"方法比较结果已保存到: {output_path}")
        
        return comparison
    
    def _save_results(self, result: EvaluationResult, matching_result: Any) -> None:
        """保存评估结果
        
        Args:
            result: EvaluationResult对象
            matching_result: MatchingResult对象
        """
        # 创建方法专属目录
        method_dir = Path(self.config.output_dir) / result.method_name.replace(' ', '_')
        method_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 保存总体结果
        overall_path = method_dir / "overall_metrics.json"
        with open(overall_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        # 2. 保存匹配详情
        matching_details = {
            'total_matches': len(matching_result.matches),
            'total_false_positives': len(matching_result.unmatched_predictions),
            'total_false_negatives': len(matching_result.unmatched_ground_truth),
            'matches': [
                {
                    'prediction_id': m.prediction_id,
                    'ground_truth_id': m.ground_truth_id,
                    'smell_type': m.smell_type,
                    'match_score': m.match_score
                }
                for m in matching_result.matches
            ],
            'false_positives': matching_result.unmatched_predictions,
            'false_negatives': matching_result.unmatched_ground_truth
        }
        
        matching_path = method_dir / "matching_details.json"
        with open(matching_path, 'w', encoding='utf-8') as f:
            json.dump(matching_details, f, indent=2, ensure_ascii=False)
        
        # 3. 保存每个Smell类型的指标
        if result.per_smell_metrics:
            per_smell_path = method_dir / "per_smell_metrics.json"
            per_smell_data = {
                smell_type: metrics.to_dict()
                for smell_type, metrics in result.per_smell_metrics.items()
            }
            with open(per_smell_path, 'w', encoding='utf-8') as f:
                json.dump(per_smell_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"评估结果已保存到: {method_dir}")


class GroundTruthLoader:
    """Ground Truth数据加载器"""
    
    @staticmethod
    def load_from_json(file_path: str) -> List[Dict]:
        """从JSON文件加载Ground Truth
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Ground Truth Smell列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 确保每个Smell有必要的字段
        for smell in data:
            if 'id' not in smell:
                smell['id'] = f"{smell['file_path']}:{smell['line_number']}:{smell['smell_type']}"
        
        return data
    
    @staticmethod
    def load_from_directory(directory: str) -> Dict[str, List[Dict]]:
        """从目录加载多个Ground Truth文件
        
        Args:
            directory: 目录路径
            
        Returns:
            按文件分组的Ground Truth字典
        """
        ground_truth_by_file = {}
        
        dir_path = Path(directory)
        for json_file in dir_path.glob("*.json"):
            file_name = json_file.stem
            ground_truth_by_file[file_name] = GroundTruthLoader.load_from_json(str(json_file))
        
        return ground_truth_by_file
