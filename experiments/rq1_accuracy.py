"""
RQ1实验：检测准确性评估

研究问题：How accurately can the proposed approach detect pipeline smells?

实验设计：
1. 在Ground Truth数据集上运行Pipeline-aware方法
2. 计算Precision、Recall、F1-score
3. 按Smell类型分析性能
4. 生成详细的评估报告
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation import (
    Evaluator,
    EvaluationConfig,
    MatchStrategy,
    GroundTruthLoader
)
from src.smells.detector import DetectorRegistry
from src.core.pipeline import PipelineExtractor
from src.core.logger import Logger


def run_pipeline_aware_detection(file_paths: list) -> list:
    """运行Pipeline-aware检测方法
    
    Args:
        file_paths: 要检测的文件路径列表
        
    Returns:
        检测结果列表
    """
    logger = Logger.setup('RQ1', 'logs/rq1_experiment.log')
    logger.info(f"开始检测 {len(file_paths)} 个文件")
    
    extractor = PipelineExtractor()
    registry = DetectorRegistry()
    
    all_predictions = []
    
    for file_path in file_paths:
        logger.info(f"检测文件: {file_path}")
        
        # 提取Pipeline
        pipeline = extractor.extract_from_file(file_path)
        
        if pipeline is None:
            logger.warning(f"无法提取Pipeline: {file_path}")
            continue
        
        # 运行检测
        result = registry.detect_all(pipeline)
        
        # 转换为标准格式
        for smell in result.detected_smells:
            prediction = {
                'id': f"{smell.location.file_path}:{smell.location.line_number}:{smell.smell_type}",
                'smell_type': smell.smell_type,
                'file_path': smell.location.file_path,
                'line_number': smell.location.line_number,
                'severity': smell.severity,
                'description': smell.description,
                'affected_nodes': smell.affected_nodes
            }
            all_predictions.append(prediction)
        
        logger.info(f"检测到 {len(result.detected_smells)} 个Smell")
    
    logger.info(f"总共检测到 {len(all_predictions)} 个Smell")
    
    return all_predictions


def main():
    """RQ1实验主函数"""
    
    logger = Logger.setup('RQ1', 'logs/rq1_experiment.log')
    logger.info("=" * 80)
    logger.info("开始RQ1实验：检测准确性评估")
    logger.info("=" * 80)
    
    # 1. 配置评估参数
    config = EvaluationConfig(
        match_strategy=MatchStrategy.LINE_RANGE,
        line_tolerance=2,
        output_dir="experiments/results/rq1",
        save_detailed_results=True,
        calculate_per_smell_metrics=True
    )
    
    evaluator = Evaluator(config)
    
    # 2. 加载Ground Truth
    logger.info("加载Ground Truth数据...")
    
    # TODO: 替换为实际的Ground Truth文件路径
    gt_file = "data/ground_truth/ground_truth.json"
    
    if not Path(gt_file).exists():
        logger.error(f"Ground Truth文件不存在: {gt_file}")
        logger.info("请先构建Ground Truth数据集")
        logger.info("示例Ground Truth格式:")
        
        example_gt = [
            {
                "id": "example.py:10:DATA_LEAKAGE",
                "smell_type": "DATA_LEAKAGE",
                "file_path": "example.py",
                "line_number": 10,
                "severity": "CRITICAL",
                "description": "数据泄露：在train_test_split之前进行标准化",
                "affected_nodes": ["node_1", "node_2"]
            }
        ]
        
        print(json.dumps(example_gt, indent=2, ensure_ascii=False))
        return
    
    ground_truth = GroundTruthLoader.load_from_json(gt_file)
    logger.info(f"加载了 {len(ground_truth)} 个Ground Truth Smell")
    
    # 3. 获取要检测的文件列表
    file_paths = list(set(gt['file_path'] for gt in ground_truth))
    logger.info(f"需要检测 {len(file_paths)} 个文件")
    
    # 4. 运行Pipeline-aware检测
    logger.info("运行Pipeline-aware检测...")
    predictions = run_pipeline_aware_detection(file_paths)
    
    # 5. 执行评估
    logger.info("执行评估...")
    result = evaluator.evaluate(
        predictions=predictions,
        ground_truth=ground_truth,
        method_name="Pipeline-aware"
    )
    
    # 6. 输出结果
    logger.info("=" * 80)
    logger.info("RQ1实验结果")
    logger.info("=" * 80)
    
    summary = result.get_summary()
    
    logger.info(f"方法: {summary['method']}")
    logger.info(f"Precision: {summary['precision']:.4f}")
    logger.info(f"Recall: {summary['recall']:.4f}")
    logger.info(f"F1-score: {summary['f1_score']:.4f}")
    logger.info(f"总预测数: {summary['total_predictions']}")
    logger.info(f"Ground Truth数: {summary['total_ground_truth']}")
    logger.info(f"运行时间: {summary['runtime_ms']:.2f}ms")
    
    # 7. 按Smell类型输出结果
    logger.info("\n按Smell类型的性能:")
    logger.info("-" * 80)
    
    for smell_type, metrics in result.per_smell_metrics.items():
        if smell_type == 'overall':
            continue
        
        logger.info(f"\n{smell_type}:")
        logger.info(f"  Precision: {metrics.precision:.4f}")
        logger.info(f"  Recall: {metrics.recall:.4f}")
        logger.info(f"  F1-score: {metrics.f1_score:.4f}")
        logger.info(f"  预测数: {metrics.total_predictions}")
        logger.info(f"  真实数: {metrics.total_ground_truth}")
    
    # 8. 保存结果摘要
    output_dir = Path(config.output_dir)
    summary_file = output_dir / "rq1_summary.json"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'overall': summary,
            'per_smell': {
                smell_type: metrics.to_dict()
                for smell_type, metrics in result.per_smell_metrics.items()
            }
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n结果已保存到: {output_dir}")
    logger.info("=" * 80)
    logger.info("RQ1实验完成")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
