"""
Ground Truth数据集构建工具

提供交互式界面，帮助标注者构建Ground Truth数据集。
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.smells.taxonomy import get_all_smells, SmellCategory
from src.core.logger import Logger


class GroundTruthBuilder:
    """Ground Truth构建器"""
    
    def __init__(self, output_dir: str = "data/ground_truth"):
        """初始化构建器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = Logger.setup('GTBuilder', 'logs/ground_truth_builder.log')
        
        # 加载Smell分类体系
        self.all_smells = get_all_smells()
        self.smell_dict = {smell.name: smell for smell in self.all_smells}
    
    def create_template(self, file_path: str) -> Dict:
        """为文件创建Ground Truth模板
        
        Args:
            file_path: 源文件路径
            
        Returns:
            Ground Truth模板字典
        """
        template = {
            'file_path': file_path,
            'annotator': '',  # 标注者姓名
            'annotation_date': '',  # 标注日期
            'smells': []
        }
        
        return template
    
    def add_smell_annotation(self, template: Dict, smell_type: str,
                           line_number: int, description: str = "",
                           affected_nodes: List[str] = None) -> None:
        """添加Smell标注
        
        Args:
            template: Ground Truth模板
            smell_type: Smell类型
            line_number: 行号
            description: 描述（可选）
            affected_nodes: 影响的节点列表（可选）
        """
        if smell_type not in self.smell_dict:
            self.logger.warning(f"未知的Smell类型: {smell_type}")
            return
        
        smell_info = self.smell_dict[smell_type]
        
        smell_annotation = {
            'id': f"{template['file_path']}:{line_number}:{smell_type}",
            'smell_type': smell_type,
            'file_path': template['file_path'],
            'line_number': line_number,
            'severity': smell_info.severity.value,
            'category': smell_info.category.value,
            'description': description or smell_info.description,
            'affected_nodes': affected_nodes or []
        }
        
        template['smells'].append(smell_annotation)
        self.logger.info(f"添加标注: {smell_type} at line {line_number}")
    
    def save_template(self, template: Dict, filename: str = None) -> None:
        """保存Ground Truth模板
        
        Args:
            template: Ground Truth模板
            filename: 输出文件名（可选）
        """
        if filename is None:
            # 使用源文件名生成输出文件名
            source_file = Path(template['file_path']).stem
            filename = f"{source_file}_gt.json"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Ground Truth已保存到: {output_path}")
    
    def merge_annotations(self, annotation_files: List[str],
                         output_file: str = "ground_truth.json") -> None:
        """合并多个标注文件
        
        Args:
            annotation_files: 标注文件路径列表
            output_file: 输出文件名
        """
        all_smells = []
        
        for file_path in annotation_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'smells' in data:
                all_smells.extend(data['smells'])
            else:
                # 假设文件直接包含Smell列表
                all_smells.extend(data)
        
        output_path = self.output_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_smells, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"合并了 {len(all_smells)} 个标注到: {output_path}")
    
    def validate_annotation(self, template: Dict) -> List[str]:
        """验证标注的完整性和一致性
        
        Args:
            template: Ground Truth模板
            
        Returns:
            错误信息列表
        """
        errors = []
        
        # 检查必填字段
        if not template.get('file_path'):
            errors.append("缺少file_path字段")
        
        if not template.get('annotator'):
            errors.append("缺少annotator字段")
        
        if not template.get('annotation_date'):
            errors.append("缺少annotation_date字段")
        
        # 检查每个Smell标注
        for i, smell in enumerate(template.get('smells', [])):
            if not smell.get('smell_type'):
                errors.append(f"Smell {i}: 缺少smell_type")
            
            if not smell.get('line_number'):
                errors.append(f"Smell {i}: 缺少line_number")
            
            if smell.get('smell_type') not in self.smell_dict:
                errors.append(f"Smell {i}: 未知的smell_type: {smell.get('smell_type')}")
        
        return errors
    
    def print_smell_catalog(self) -> None:
        """打印Smell分类目录"""
        print("\n" + "=" * 80)
        print("Pipeline Smell分类目录")
        print("=" * 80)
        
        # 按类别分组
        by_category = {}
        for smell in self.all_smells:
            category = smell.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(smell)
        
        # 打印每个类别
        for category, smells in by_category.items():
            print(f"\n{category} ({len(smells)}种):")
            print("-" * 80)
            
            for smell in smells:
                print(f"\n  {smell.name}")
                print(f"    严重性: {smell.severity.value}")
                print(f"    描述: {smell.description[:100]}...")


def interactive_annotation():
    """交互式标注工具"""
    
    builder = GroundTruthBuilder()
    
    print("\n" + "=" * 80)
    print("Ground Truth交互式标注工具")
    print("=" * 80)
    
    # 显示Smell目录
    builder.print_smell_catalog()
    
    # 获取文件路径
    print("\n请输入要标注的文件路径:")
    file_path = input("> ").strip()
    
    if not Path(file_path).exists():
        print(f"错误: 文件不存在: {file_path}")
        return
    
    # 创建模板
    template = builder.create_template(file_path)
    
    # 获取标注者信息
    print("\n请输入标注者姓名:")
    template['annotator'] = input("> ").strip()
    
    print("\n请输入标注日期 (YYYY-MM-DD):")
    template['annotation_date'] = input("> ").strip()
    
    # 添加Smell标注
    print("\n开始标注Smell (输入'done'完成标注)")
    
    while True:
        print("\n" + "-" * 80)
        print("输入Smell类型 (或'list'查看所有类型, 'done'完成):")
        smell_type = input("> ").strip().upper()
        
        if smell_type == 'DONE':
            break
        
        if smell_type == 'LIST':
            builder.print_smell_catalog()
            continue
        
        if smell_type not in builder.smell_dict:
            print(f"错误: 未知的Smell类型: {smell_type}")
            continue
        
        print("输入行号:")
        try:
            line_number = int(input("> ").strip())
        except ValueError:
            print("错误: 行号必须是整数")
            continue
        
        print("输入描述 (可选, 直接回车跳过):")
        description = input("> ").strip()
        
        print("输入影响的节点 (逗号分隔, 可选):")
        affected_nodes_str = input("> ").strip()
        affected_nodes = [n.strip() for n in affected_nodes_str.split(',') if n.strip()]
        
        builder.add_smell_annotation(
            template, smell_type, line_number,
            description, affected_nodes
        )
        
        print(f"✓ 已添加 {smell_type} 标注")
    
    # 验证标注
    errors = builder.validate_annotation(template)
    
    if errors:
        print("\n警告: 标注存在以下问题:")
        for error in errors:
            print(f"  - {error}")
        
        print("\n是否仍要保存? (y/n)")
        if input("> ").strip().lower() != 'y':
            print("已取消保存")
            return
    
    # 保存标注
    builder.save_template(template)
    
    print(f"\n✓ 标注完成! 共标注了 {len(template['smells'])} 个Smell")


def batch_annotation_from_csv():
    """从CSV文件批量导入标注"""
    
    import csv
    
    builder = GroundTruthBuilder()
    
    print("\n" + "=" * 80)
    print("从CSV批量导入标注")
    print("=" * 80)
    
    print("\nCSV格式要求:")
    print("file_path,smell_type,line_number,description,affected_nodes")
    print("\n请输入CSV文件路径:")
    csv_path = input("> ").strip()
    
    if not Path(csv_path).exists():
        print(f"错误: 文件不存在: {csv_path}")
        return
    
    # 按文件分组
    annotations_by_file = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            file_path = row['file_path']
            
            if file_path not in annotations_by_file:
                annotations_by_file[file_path] = builder.create_template(file_path)
            
            affected_nodes = []
            if row.get('affected_nodes'):
                affected_nodes = [n.strip() for n in row['affected_nodes'].split(',')]
            
            builder.add_smell_annotation(
                annotations_by_file[file_path],
                smell_type=row['smell_type'].upper(),
                line_number=int(row['line_number']),
                description=row.get('description', ''),
                affected_nodes=affected_nodes
            )
    
    # 保存每个文件的标注
    for file_path, template in annotations_by_file.items():
        builder.save_template(template)
    
    print(f"\n✓ 批量导入完成! 共处理了 {len(annotations_by_file)} 个文件")


def main():
    """主函数"""
    
    print("\n" + "=" * 80)
    print("Ground Truth构建工具")
    print("=" * 80)
    
    print("\n请选择模式:")
    print("1. 交互式标注")
    print("2. 从CSV批量导入")
    print("3. 合并标注文件")
    print("4. 查看Smell目录")
    
    choice = input("\n> ").strip()
    
    if choice == '1':
        interactive_annotation()
    elif choice == '2':
        batch_annotation_from_csv()
    elif choice == '3':
        builder = GroundTruthBuilder()
        
        print("\n请输入要合并的标注文件路径 (逗号分隔):")
        files_str = input("> ").strip()
        files = [f.strip() for f in files_str.split(',')]
        
        print("\n请输入输出文件名:")
        output_file = input("> ").strip()
        
        builder.merge_annotations(files, output_file)
    elif choice == '4':
        builder = GroundTruthBuilder()
        builder.print_smell_catalog()
    else:
        print("无效的选择")


if __name__ == '__main__':
    main()
