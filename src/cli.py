"""
命令行接口模块

提供Pipeline Smell Detection系统的命令行工具。
支持单文件检测、批量检测、报告生成等功能。
"""

import sys
import click
from pathlib import Path
from typing import Optional

from src.core.logger import Logger, LogLevel
from src.core.config import ConfigManager
from src.core.reporter import create_reporter
from src.smells.detector import DetectorRegistry
from src.core.pipeline import PipelineExtractor


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--log-file', type=click.Path(), help='日志文件路径')
def cli(verbose: bool, log_file: Optional[str]):
    """Pipeline Smell Detection工具
    
    自动检测数据准备流程中的结构性代码异味。
    """
    # 配置日志
    log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
    Logger.setup(level=log_level, log_file=log_file)
    
    Logger.info("Pipeline Smell Detection System启动")


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出报告路径')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'visual']), 
              default='text', help='报告格式')
@click.option('--categories', type=str, help='检测的Smell类别（逗号分隔）')
@click.option('--severity', type=str, help='最小严重性级别（CRITICAL/HIGH/MEDIUM/LOW）')
def detect(file_path: str, output: Optional[str], format: str, 
           categories: Optional[str], severity: Optional[str]):
    """检测单个Python文件中的Pipeline Smell
    
    FILE_PATH: 要检测的Python文件路径
    """
    Logger.info(f"开始检测文件: {file_path}")
    
    try:
        # 1. 提取Pipeline
        extractor = PipelineExtractor()
        pipeline = extractor.extract_from_file(file_path)
        
        if not pipeline:
            Logger.warning(f"文件中未找到Pipeline: {file_path}")
            sys.exit(0)
        
        Logger.info(f"成功提取Pipeline: {len(pipeline.get_nodes())} 个操作节点")
        
        # 2. 运行检测器
        registry = DetectorRegistry()
        
        # 解析类别过滤器
        category_list = None
        if categories:
            category_list = [c.strip().upper() for c in categories.split(',')]
        
        # 执行检测
        result = registry.detect_all(pipeline, categories=category_list)
        
        # 3. 过滤严重性级别
        if severity:
            severity_order = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            min_order = severity_order.get(severity.upper(), 2)
            result.detected_smells = [
                smell for smell in result.detected_smells
                if severity_order.get(smell.severity.value, 2) >= min_order
            ]
        
        # 4. 生成报告
        output_path = output or f"{file_path}.report.{format}"
        reporter = create_reporter(format)
        reporter.generate(result, output_path)
        
        # 5. 输出摘要
        summary = result.get_summary()
        click.echo(f"\n📊 检测完成:")
        click.echo(f"   文件: {file_path}")
        click.echo(f"   节点数: {result.pipeline_info['num_nodes']}")
        click.echo(f"   检测到Smell: {summary['total_smells']}")
        click.echo(f"   运行时间: {result.runtime_ms:.2f} ms")
        click.echo(f"   报告已保存: {output_path}")
        
    except Exception as e:
        Logger.error(f"检测失败: {e}")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--output', '-o', type=click.Path(), help='输出报告目录')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'visual']), 
              default='json', help='报告格式')
@click.option('--recursive', '-r', is_flag=True, help='递归遍历子目录')
@click.option('--pattern', default='*.py', help='文件匹配模式')
def batch(directory: str, output: Optional[str], format: str, 
          recursive: bool, pattern: str):
    """批量检测目录中的Python文件
    
    DIRECTORY: 要检测的目录路径
    """
    Logger.info(f"开始批量检测目录: {directory}")
    
    # 查找Python文件
    dir_path = Path(directory)
    if recursive:
        files = list(dir_path.rglob(pattern))
    else:
        files = list(dir_path.glob(pattern))
    
    if not files:
        Logger.warning(f"未找到匹配的文件: {pattern}")
        sys.exit(0)
    
    Logger.info(f"找到 {len(files)} 个文件")
    
    # 准备输出目录
    output_dir = Path(output or f"{directory}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 批量处理
    results = []
    from tqdm import tqdm
    
    for file_path in tqdm(files, desc="检测文件"):
        try:
            extractor = PipelineExtractor()
            pipeline = extractor.extract_from_file(str(file_path))
            
            if pipeline:
                registry = DetectorRegistry()
                result = registry.detect_all(pipeline)
                results.append(result)
                
                # 保存单个报告
                relative_path = file_path.relative_to(directory)
                output_file = output_dir / f"{relative_path}.{format}"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                reporter = create_reporter(format)
                reporter.generate(result, str(output_file))
                
        except Exception as e:
            Logger.warning(f"文件 {file_path} 处理失败: {e}")
    
    # 生成汇总报告
    summary_file = output_dir / f"summary.{format}"
    _generate_batch_summary(results, summary_file)
    
    click.echo(f"\n📊 批量检测完成:")
    click.echo(f"   处理文件数: {len(files)}")
    click.echo(f"   成功检测: {len(results)}")
    click.echo(f"   汇总报告: {summary_file}")


@cli.command()
@click.argument('ground_truth', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出结果路径')
def evaluate(ground_truth: str, output: Optional[str]):
    """运行评估实验(RQ1/RQ2)
    
    GROUND_TRUTH: Ground Truth数据集路径（JSON格式）
    """
    Logger.info("开始评估实验")
    click.echo("⚠️  评估功能即将实现...")
    # TODO: 实现评估逻辑
    sys.exit(0)


@cli.command()
def list_smells():
    """列出所有支持的Pipeline Smell类型"""
    registry = DetectorRegistry()
    smell_types = registry.get_supported_smell_types()
    
    click.echo("支持的Pipeline Smell类型")
    click.echo("=" * 50)
    
    categories = {}
    for smell_type in sorted(smell_types):
        # 从detector模块导入Smell定义
        try:
            from src.smells.taxonomy import (
                DATA_LEAKAGE, MISSING_EVALUATION, MODULE_ORDER_VIOLATION,
                REPEATED_TRANSFORM, EXCESSIVE_COPY, REDUNDANT_OPERATION,
                MISSING_RANDOM_SEED, MISSING_VALIDATION, MISSING_DATA_PROFILING,
                INEFFICIENT_AGGREGATION, UNNECESSARY_MATERIALIZATION, 
                LARGE_DATAFRAME_OPERATION,
                CIRCULAR_DEPENDENCY, IMPROPER_MODULE_COHESION, PIPELINE_FRAGMENTATION,
                HARDCODED_PARAMETERS, LACK_OF_VERSION_CONTROL, NON_DETERMINISTIC_ORDER
            )
            
            smell_map = {
                'DATA_LEAKAGE': DATA_LEAKAGE,
                'MISSING_EVALUATION': MISSING_EVALUATION,
                'MODULE_ORDER_VIOLATION': MODULE_ORDER_VIOLATION,
                'REPEATED_TRANSFORM': REPEATED_TRANSFORM,
                'EXCESSIVE_COPY': EXCESSIVE_COPY,
                'REDUNDANT_OPERATION': REDUNDANT_OPERATION,
                'MISSING_RANDOM_SEED': MISSING_RANDOM_SEED,
                'MISSING_VALIDATION': MISSING_VALIDATION,
                'MISSING_DATA_PROFILING': MISSING_DATA_PROFILING,
                'INEFFICIENT_AGGREGATION': INEFFICIENT_AGGREGATION,
                'UNNECESSARY_MATERIALIZATION': UNNECESSARY_MATERIALIZATION,
                'LARGE_DATAFRAME_OPERATION': LARGE_DATAFRAME_OPERATION,
                'CIRCULAR_DEPENDENCY': CIRCULAR_DEPENDENCY,
                'IMPROPER_MODULE_COHESION': IMPROPER_MODULE_COHESION,
                'PIPELINE_FRAGMENTATION': PIPELINE_FRAGMENTATION,
                'HARDCODED_PARAMETERS': HARDCODED_PARAMETERS,
                'LACK_OF_VERSION_CONTROL': LACK_OF_VERSION_CONTROL,
                'NON_DETERMINISTIC_ORDER': NON_DETERMINISTIC_ORDER
            }
            
            smell_obj = smell_map.get(smell_type)
            if smell_obj:
                category = smell_obj.category.value
                if category not in categories:
                    categories[category] = []
                categories[category].append(smell_obj)
        except ImportError:
            continue
    
    # 按类别输出
    for category, smells in sorted(categories.items()):
        click.echo(f"\n{category}")
        click.echo("-" * 50)
        for smell in smells:
            click.echo(f"  • {smell.name} ({smell.severity.value})")
            click.echo(f"    {smell.description}")


def _generate_batch_summary(results: list, output_path: str):
    """生成批量检测汇总报告
    
    Args:
        results: 检测结果列表
        output_path: 输出文件路径
    """
    total_smells = sum(len(r.detected_smells) for r in results)
    files_with_smells = sum(1 for r in results if r.detected_smells)
    
    summary_content = f"""# Batch Detection Summary

## Statistics

- **Total Files**: {len(results)}
- **Files with Smells**: {files_with_smells}
- **Total Smells**: {total_smells}
- **Avg Smells per File**: {total_smells / len(results):.2f}

## Top Files by Smell Count

"""
    
    # 按Smell数量排序
    sorted_results = sorted(
        results,
        key=lambda r: len(r.detected_smells),
        reverse=True
    )
    
    for i, result in enumerate(sorted_results[:10], 1):
        summary_content += f"{i}. {result.pipeline_info['file_path']}: "
        summary_content += f"{len(result.detected_smells)} smells\n"
    
    Path(output_path).write_text(summary_content, encoding='utf-8')


if __name__ == '__main__':
    cli()
