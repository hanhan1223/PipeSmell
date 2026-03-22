"""
RQ2实验：检测能力对比

研究问题：Can the proposed method detect pipeline-level smells that existing tools fail to detect?

实验设计：
1. 在相同数据集上运行多个方法：
   - Pipeline-aware（本方法）
   - Baseline-Keyword
   - Baseline-Heuristic
   - Baseline-SonarQube
   - Baseline-PMD
2. 比较各方法检测到的Smell类型数量
3. 分析Pipeline-aware独有的检测能力
4. 统计显著性检验
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation import (
    Evaluator,
    EvaluationConfig,
    MatchStrategy,
    GroundTruthLoader,
    StatisticalTests,
    MultiMethodComparison
)
from src.smells.detector import DetectorRegistry
from src.core.pipeline import PipelineExtractor
from src.baseline.keyword_detector import KeywordBaseline
from src.baseline.heuristic_detector import HeuristicBaseline
from src.baseline.sonarqube_adapter import SonarQubeBaseline
from src.baseline.pmd_adapter import PMDBaseline
from src.core.logger import Logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GT_CANDIDATES = [
    PROJECT_ROOT / "dataset" / "ground_truth.json",
    PROJECT_ROOT / "data" / "ground_truth" / "ground_truth.json",
]


def _resolve_gt_path() -> Path:
    for p in DEFAULT_GT_CANDIDATES:
        if p.is_file():
            return p
    return DEFAULT_GT_CANDIDATES[0]


def _all_files_from_annotations(gt_path: Path) -> List[str]:
    try:
        with open(gt_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict) or "annotations" not in data:
        return []
    root = gt_path.parent.resolve()
    out: List[str] = []
    for ann in data["annotations"]:
        fn = ann.get("file") or ann.get("file_path")
        if fn:
            out.append(str((root / fn).resolve()))
    return out


def _smell_instances_to_predictions(smells) -> List[Dict]:
    """将 SmellInstance 列表转为评估器使用的 prediction 字典列表。"""
    preds: List[Dict] = []
    for smell in smells:
        fp = smell.location.file_path
        pred_path = str(Path(fp).resolve()) if fp else fp
        preds.append(
            {
                "id": f"{pred_path}:{smell.location.line_number}:{smell.smell_type}",
                "smell_type": smell.smell_type,
                "file_path": pred_path,
                "line_number": smell.location.line_number,
                "severity": smell.severity,
                "description": smell.description,
                "affected_nodes": smell.affected_nodes,
            }
        )
    return preds


def run_pipeline_aware(file_paths: List[str]) -> List[Dict]:
    """运行Pipeline-aware方法"""
    logger = Logger.setup('RQ2', 'logs/rq2_experiment.log')
    logger.info("运行Pipeline-aware方法...")
    
    extractor = PipelineExtractor()
    registry = DetectorRegistry()
    
    all_predictions = []
    
    for file_path in file_paths:
        pipeline = extractor.extract_from_file(file_path)
        if pipeline is None:
            continue
        
        result = registry.detect_all(pipeline)
        
        all_predictions.extend(_smell_instances_to_predictions(result.detected_smells))
    
    logger.info(f"Pipeline-aware检测到 {len(all_predictions)} 个Smell")
    return all_predictions


def run_baseline_keyword(file_paths: List[str]) -> List[Dict]:
    """运行关键词基线方法"""
    logger = Logger.setup('RQ2', 'logs/rq2_experiment.log')
    logger.info("运行Keyword基线方法...")
    
    baseline = KeywordBaseline()
    all_predictions = []
    
    for file_path in file_paths:
        smells = baseline.detect(file_path)
        all_predictions.extend(_smell_instances_to_predictions(smells))

    logger.info(f"Keyword基线检测到 {len(all_predictions)} 个Smell")
    return all_predictions


def run_baseline_heuristic(file_paths: List[str]) -> List[Dict]:
    """运行启发式基线方法"""
    logger = Logger.setup('RQ2', 'logs/rq2_experiment.log')
    logger.info("运行Heuristic基线方法...")
    
    extractor = PipelineExtractor()
    registry = DetectorRegistry()
    baseline = HeuristicBaseline()
    all_predictions = []

    for file_path in file_paths:
        pipeline = extractor.extract_from_file(file_path)
        if pipeline is None:
            continue
        module_sequence = registry._extract_module_sequence(pipeline)
        smells = baseline.detect(pipeline, module_sequence)
        all_predictions.extend(_smell_instances_to_predictions(smells))

    logger.info(f"Heuristic基线检测到 {len(all_predictions)} 个Smell")
    return all_predictions


def run_baseline_sonarqube(file_paths: List[str]) -> List[Dict]:
    """运行SonarQube基线方法"""
    logger = Logger.setup('RQ2', 'logs/rq2_experiment.log')
    logger.info("运行SonarQube基线方法...")
    
    baseline = SonarQubeBaseline()
    all_predictions = []
    
    for file_path in file_paths:
        smells = baseline.detect(file_path)
        all_predictions.extend(_smell_instances_to_predictions(smells))

    logger.info(f"SonarQube基线检测到 {len(all_predictions)} 个Smell")
    return all_predictions


def run_baseline_pmd(file_paths: List[str]) -> List[Dict]:
    """运行PMD基线方法"""
    logger = Logger.setup('RQ2', 'logs/rq2_experiment.log')
    logger.info("运行PMD基线方法...")
    
    baseline = PMDBaseline()
    all_predictions = []
    
    for file_path in file_paths:
        smells = baseline.detect(file_path)
        all_predictions.extend(_smell_instances_to_predictions(smells))

    logger.info(f"PMD基线检测到 {len(all_predictions)} 个Smell")
    return all_predictions


def analyze_coverage(results: Dict[str, List[Dict]]) -> Dict:
    """分析各方法的覆盖能力
    
    Args:
        results: 方法名到检测结果的字典
        
    Returns:
        覆盖能力分析结果
    """
    analysis = {
        'smell_types_by_method': {},
        'unique_to_pipeline_aware': set(),
        'common_to_all': set(),
        'coverage_matrix': {}
    }
    
    # 统计每个方法检测到的Smell类型
    for method_name, predictions in results.items():
        smell_types = set(p['smell_type'] for p in predictions)
        analysis['smell_types_by_method'][method_name] = list(smell_types)
    
    # 找出Pipeline-aware独有的Smell类型
    pipeline_aware_types = set(analysis['smell_types_by_method'].get('Pipeline-aware', []))
    
    for method_name, smell_types in analysis['smell_types_by_method'].items():
        if method_name != 'Pipeline-aware':
            pipeline_aware_types -= set(smell_types)
    
    analysis['unique_to_pipeline_aware'] = list(pipeline_aware_types)
    
    # 找出所有方法都能检测到的Smell类型
    if analysis['smell_types_by_method']:
        common_types = set(analysis['smell_types_by_method'][list(results.keys())[0]])
        
        for smell_types in analysis['smell_types_by_method'].values():
            common_types &= set(smell_types)
        
        analysis['common_to_all'] = list(common_types)
    
    # 构建覆盖矩阵
    all_smell_types = set()
    for smell_types in analysis['smell_types_by_method'].values():
        all_smell_types.update(smell_types)
    
    for smell_type in all_smell_types:
        analysis['coverage_matrix'][smell_type] = {}
        
        for method_name, smell_types in analysis['smell_types_by_method'].items():
            analysis['coverage_matrix'][smell_type][method_name] = smell_type in smell_types
    
    return analysis


def main():
    """RQ2实验主函数"""
    
    logger = Logger.setup('RQ2', 'logs/rq2_experiment.log')
    logger.info("=" * 80)
    logger.info("开始RQ2实验：检测能力对比")
    logger.info("=" * 80)
    
    # 1. 配置评估参数
    config = EvaluationConfig(
        match_strategy=MatchStrategy.LINE_RANGE,
        line_tolerance=8,
        output_dir="experiments/results/rq2",
        save_detailed_results=True,
        calculate_per_smell_metrics=True
    )
    
    evaluator = Evaluator(config)
    
    # 2. 加载Ground Truth（默认 dataset/ground_truth.json）
    logger.info("加载Ground Truth数据...")
    
    gt_file = _resolve_gt_path()
    
    if not gt_file.is_file():
        logger.error(f"Ground Truth文件不存在: {gt_file}")
        logger.info("请将标注文件放在以下路径之一:")
        for p in DEFAULT_GT_CANDIDATES:
            logger.info(f"  - {p}")
        return
    
    ground_truth = GroundTruthLoader.load_from_json(str(gt_file))
    logger.info(f"加载了 {len(ground_truth)} 个Ground Truth Smell")

    # 3. 待测文件：GT 中出现的文件 ∪ annotations 中的文件（含 smells 为空的负例）
    from_gt = {str(Path(gt["file_path"]).resolve()) for gt in ground_truth}
    from_ann = set(_all_files_from_annotations(gt_file))
    file_paths = sorted(from_gt | from_ann)
    logger.info(f"需要检测 {len(file_paths)} 个文件")
    
    # 4. 运行所有方法
    logger.info("\n运行所有检测方法...")
    
    all_predictions = {
        'Pipeline-aware': run_pipeline_aware(file_paths),
        'Baseline-Keyword': run_baseline_keyword(file_paths),
        'Baseline-Heuristic': run_baseline_heuristic(file_paths),
        'Baseline-SonarQube': run_baseline_sonarqube(file_paths),
        'Baseline-PMD': run_baseline_pmd(file_paths)
    }
    
    # 5. 评估所有方法
    logger.info("\n评估所有方法...")
    
    evaluation_results = []
    
    for method_name, predictions in all_predictions.items():
        logger.info(f"\n评估 {method_name}...")
        
        result = evaluator.evaluate(
            predictions=predictions,
            ground_truth=ground_truth,
            method_name=method_name
        )
        
        evaluation_results.append(result)
        
        summary = result.get_summary()
        logger.info(f"  Precision: {summary['precision']:.4f}")
        logger.info(f"  Recall: {summary['recall']:.4f}")
        logger.info(f"  F1-score: {summary['f1_score']:.4f}")
    
    # 6. 方法比较
    logger.info("\n生成方法比较...")
    comparison = evaluator.compare_methods(evaluation_results)
    
    logger.info("\n方法排名（按F1分数）:")
    for i, method in enumerate(comparison['methods'], 1):
        logger.info(f"{i}. {method['name']}: F1={method['f1_score']:.4f}, "
                   f"P={method['precision']:.4f}, R={method['recall']:.4f}")
    
    # 7. 覆盖能力分析
    logger.info("\n分析覆盖能力...")
    coverage_analysis = analyze_coverage(all_predictions)
    
    logger.info(f"\nPipeline-aware独有的Smell类型: {len(coverage_analysis['unique_to_pipeline_aware'])}")
    for smell_type in coverage_analysis['unique_to_pipeline_aware']:
        logger.info(f"  - {smell_type}")
    
    logger.info(f"\n所有方法都能检测的Smell类型: {len(coverage_analysis['common_to_all'])}")
    for smell_type in coverage_analysis['common_to_all']:
        logger.info(f"  - {smell_type}")
    
    # 8. 统计显著性检验
    logger.info("\n执行统计显著性检验...")
    
    # 收集每个方法在每个文件上的F1分数
    method_scores = {}
    
    for result in evaluation_results:
        if result.per_file_metrics:
            scores = [metrics.f1_score for metrics in result.per_file_metrics.values()]
            method_scores[result.method_name] = scores
    
    if len(method_scores) >= 2 and all(len(scores) > 0 for scores in method_scores.values()):
        comparison_tool = MultiMethodComparison(alpha=0.05)
        statistical_results = comparison_tool.compare_all(method_scores)
        
        # 保存统计检验结果
        output_dir = Path(config.output_dir)
        stats_file = output_dir / "statistical_tests.json"
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistical_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"统计检验结果已保存到: {stats_file}")
        
        # 生成报告
        report = comparison_tool.generate_report(statistical_results)
        report_file = output_dir / "statistical_report.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"统计报告已保存到: {report_file}")
    
    # 9. 保存覆盖能力分析
    output_dir = Path(config.output_dir)
    coverage_file = output_dir / "coverage_analysis.json"
    
    # 转换set为list以便JSON序列化
    coverage_analysis_json = {
        'smell_types_by_method': coverage_analysis['smell_types_by_method'],
        'unique_to_pipeline_aware': list(coverage_analysis['unique_to_pipeline_aware']),
        'common_to_all': list(coverage_analysis['common_to_all']),
        'coverage_matrix': coverage_analysis['coverage_matrix']
    }
    
    with open(coverage_file, 'w', encoding='utf-8') as f:
        json.dump(coverage_analysis_json, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n覆盖能力分析已保存到: {coverage_file}")
    
    logger.info("=" * 80)
    logger.info("RQ2实验完成")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
