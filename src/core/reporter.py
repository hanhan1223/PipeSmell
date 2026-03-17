"""
报告生成器模块

提供多种格式的检测报告生成功能，包括文本报告、JSON报告和可视化报告。
支持自定义报告内容和格式，便于集成到不同的工作流中。
"""

import json
from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict

from src.core.logger import Logger
from src.smells.detector import DetectionResult, SmellInstance, LocationInfo
from src.smells.taxonomy import SeverityLevel


class ReporterBase:
    """报告生成器基类
    
    提供报告生成的通用接口和辅助方法。
    """
    
    def __init__(self):
        """初始化报告生成器"""
        pass
    
    def generate(self, result: DetectionResult, output_path: str) -> None:
        """生成报告
        
        Args:
            result: 检测结果对象
            output_path: 输出文件路径
        """
        raise NotImplementedError("子类必须实现generate方法")
    
    def _format_location(self, location: LocationInfo) -> str:
        """格式化位置信息
        
        Args:
            location: 位置信息对象
            
        Returns:
            格式化的字符串
        """
        return f"{location.file_path}:{location.line_number}"


class TextReporter(ReporterBase):
    """文本报告生成器
    
    生成人类可读的Markdown格式报告。
    包含Pipeline摘要、Smell详细列表和修复建议。
    """
    
    def generate(self, result: DetectionResult, output_path: str) -> None:
        """生成Markdown格式的文本报告
        
        Args:
            result: 检测结果对象
            output_path: 输出文件路径
        """
        lines = []
        
        # 报告标题
        lines.append("# Pipeline Smell Detection Report")
        lines.append("")
        
        # Pipeline信息
        lines.append("## Pipeline Information")
        lines.append("")
        for key, value in result.pipeline_info.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
        
        # 执行统计
        summary = result.get_summary()
        lines.append("## Detection Summary")
        lines.append("")
        lines.append(f"- **Total Smells**: {summary['total_smells']}")
        lines.append(f"- **Detection Runtime**: {result.runtime_ms:.2f} ms")
        lines.append("")
        
        # 按严重性统计
        lines.append("### By Severity")
        lines.append("")
        for severity, count in sorted(summary['by_severity'].items()):
            lines.append(f"- **{severity}**: {count}")
        lines.append("")
        
        # 按类别统计
        lines.append("### By Category")
        lines.append("")
        for category, count in sorted(summary['by_category'].items()):
            lines.append(f"- **{category}**: {count}")
        lines.append("")
        
        # Smell详细列表
        if result.detected_smells:
            lines.append("## Detected Smells")
            lines.append("")
            
            # 按严重性分组
            smells_by_severity = defaultdict(list)
            for smell in result.detected_smells:
                smells_by_severity[smell.severity.value].append(smell)
            
            # 按严重性排序输出（CRITICAL -> LOW）
            severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
            for severity in severity_order:
                if severity in smells_by_severity:
                    lines.append(f"### {severity}")
                    lines.append("")
                    
                    # 按行号排序
                    sorted_smells = sorted(
                        smells_by_severity[severity],
                        key=lambda s: s.location.line_number
                    )
                    
                    for i, smell in enumerate(sorted_smells, 1):
                        lines.append(f"#### {i}. {smell.smell_type}")
                        lines.append("")
                        lines.append(f"**Location**: {self._format_location(smell.location)}")
                        lines.append("")
                        lines.append(f"**Description**: {smell.description}")
                        
                        if smell.affected_node_ids:
                            lines.append(f"**Affected Nodes**: {', '.join(smell.affected_node_ids)}")
                        
                        if smell.suggestion:
                            lines.append(f"**Suggestion**: {smell.suggestion}")
                        
                        lines.append("")
        else:
            lines.append("## Detected Smells")
            lines.append("")
            lines.append("✅ No pipeline smells detected!")
            lines.append("")
        
        # 修复建议摘要
        if result.detected_smells:
            lines.append("## Fix Recommendations")
            lines.append("")
            critical_count = summary['by_severity'].get('CRITICAL', 0)
            high_count = summary['by_severity'].get('HIGH', 0)
            
            if critical_count > 0:
                lines.append(f"⚠️  **{critical_count} CRITICAL issues** require immediate attention.")
                lines.append("")
            
            if high_count > 0:
                lines.append(f"🔴 **{high_count} HIGH severity issues** should be resolved soon.")
                lines.append("")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        Logger.info(f"文本报告已生成: {output_path}")


class JSONReporter(ReporterBase):
    """JSON报告生成器
    
    生成机器可读的JSON格式报告。
    适合自动化工具集成和后续数据分析。
    """
    
    def generate(self, result: DetectionResult, output_path: str) -> None:
        """生成JSON格式报告
        
        Args:
            result: 检测结果对象
            output_path: 输出文件路径
        """
        # 构建报告字典
        report = {
            'pipeline_info': result.pipeline_info,
            'summary': result.get_summary(),
            'runtime_ms': result.runtime_ms,
            'detected_smells': []
        }
        
        # 转换Smell实例为字典
        for smell in result.detected_smells:
            smell_dict = {
                'smell_type': smell.smell_type,
                'line_number': smell.location.line_number,
                'column_number': smell.location.column,
                'file_path': smell.location.file_path,
                'description': smell.description,
                'severity': smell.severity.value,
                'affected_node_ids': smell.affected_node_ids,
                'suggestion': smell.suggestion
            }
            report['detected_smells'].append(smell_dict)
        
        # 写入文件（使用ensure_ascii=False保持中文可读性）
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        Logger.info(f"JSON报告已生成: {output_path}")


class VisualReporter(ReporterBase):
    """可视化报告生成器
    
    生成Pipeline结构和Smell位置的可视化展示。
    使用graphviz或matplotlib生成图形。
    """
    
    def __init__(self, format: str = 'svg'):
        """初始化可视化报告生成器
        
        Args:
            format: 输出格式（'svg', 'png', 'pdf'等）
        """
        super().__init__()
        self.format = format
        
        # 定义严重性对应的颜色
        self.severity_colors = {
            'CRITICAL': '#ff0000',  # 红色
            'HIGH': '#ff6600',      # 橙色
            'MEDIUM': '#ffcc00',    # 黄色
            'LOW': '#66ccff'        # 蓝色
        }
    
    def generate(self, result: DetectionResult, output_path: str) -> None:
        """生成可视化报告
        
        Args:
            result: 检测结果对象
            output_path: 输出文件路径
        """
        try:
            # 尝试使用graphviz
            self._generate_graphviz(result, output_path)
        except ImportError:
            # 如果graphviz不可用，使用matplotlib
            self._generate_matplotlib(result, output_path)
    
    def _generate_graphviz(self, result: DetectionResult, output_path: str) -> None:
        """使用graphviz生成可视化
        
        Args:
            result: 检测结果对象
            output_path: 输出文件路径
        """
        try:
            from graphviz import Digraph
        except ImportError:
            raise ImportError("graphviz未安装，尝试使用matplotlib替代")
        
        # 创建有向图
        dot = Digraph(comment='Pipeline Smell Detection', format=self.format)
        dot.attr(rankdir='LR', nodesep='0.8', ranksep='1.0')
        
        # 添加节点
        # 注意：这里需要访问PipelineGraph，暂时使用占位符
        # 实际实现需要从result中提取Pipeline结构
        node_smells = self._group_smells_by_node(result.detected_smells)
        
        # 为每个节点添加到图中
        for idx, (node_id, smells) in enumerate(node_smells.items()):
            # 确定节点颜色（基于最严重的Smell）
            max_severity = self._get_max_severity(smells)
            color = self.severity_colors.get(max_severity, '#ffffff')
            
            # 创建节点标签
            label = f"Node {node_id}"
            if smells:
                label += f"\n({len(smells)} smells)"
            
            dot.node(str(node_id), label, style='filled', fillcolor=color)
        
        # 保存图
        output_file = str(Path(output_path).with_suffix(''))
        dot.render(output_file, cleanup=True)
        
        Logger.info(f"可视化报告已生成: {output_path}.{self.format}")
    
    def _generate_matplotlib(self, result: DetectionResult, output_path: str) -> None:
        """使用matplotlib生成可视化
        
        Args:
            result: 检测结果对象
            output_path: 输出文件路径
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            raise ImportError("matplotlib未安装，无法生成可视化报告")
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis('off')
        
        # 绘制Pipeline节点（简化版）
        # 注意：这里需要实际的Pipeline结构，暂时使用占位符
        num_smells = len(result.detected_smells)
        summary = result.get_summary()
        
        # 绘制统计信息
        text = f"Pipeline Smell Detection Report\n\n"
        text += f"Total Smells: {num_smells}\n"
        text += f"Runtime: {result.runtime_ms:.2f} ms\n\n"
        text += "By Severity:\n"
        for severity, count in sorted(summary['by_severity'].items()):
            text += f"  {severity}: {count}\n"
        
        ax.text(0.1, 0.9, text, fontsize=12, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 绘制严重性图例
        patches = []
        for severity, count in sorted(summary['by_severity'].items()):
            color = self.severity_colors.get(severity, '#ffffff')
            patch = mpatches.Patch(color=color, label=f'{severity} ({count})')
            patches.append(patch)
        
        if patches:
            ax.legend(handles=patches, loc='lower right')
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(output_path, format=self.format, dpi=300, bbox_inches='tight')
        plt.close()
        
        Logger.info(f"可视化报告已生成: {output_path}")
    
    def _group_smells_by_node(self, smells: List[SmellInstance]) -> Dict[str, List[SmellInstance]]:
        """按节点分组Smell
        
        Args:
            smells: Smell实例列表
            
        Returns:
            节点到Smell列表的映射
        """
        grouped = defaultdict(list)
        for smell in smells:
            # 使用行号作为临时节点ID
            node_id = str(smell.location.line_number)
            grouped[node_id].append(smell)
        return dict(grouped)
    
    def _get_max_severity(self, smells: List[SmellInstance]) -> str:
        """获取Smell列表中的最高严重性
        
        Args:
            smells: Smell实例列表
            
        Returns:
            最高严重性字符串
        """
        if not smells:
            return 'LOW'
        
        severity_order = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        max_severity = 'LOW'
        max_order = 0
        
        for smell in smells:
            order = severity_order.get(smell.severity.value, 0)
            if order > max_order:
                max_order = order
                max_severity = smell.severity.value
        
        return max_severity


def create_reporter(reporter_type: str = 'text', **kwargs) -> ReporterBase:
    """工厂函数：创建指定类型的报告生成器
    
    Args:
        reporter_type: 报告类型（'text', 'json', 'visual'）
        **kwargs: 报告生成器的额外参数
        
    Returns:
        报告生成器实例
    """
    if reporter_type == 'text':
        return TextReporter(**kwargs)
    elif reporter_type == 'json':
        return JSONReporter(**kwargs)
    elif reporter_type == 'visual':
        return VisualReporter(**kwargs)
    else:
        raise ValueError(f"未知的报告生成器类型: {reporter_type}")
