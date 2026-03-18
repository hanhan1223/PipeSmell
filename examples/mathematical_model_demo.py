"""
数学模型演示脚本

展示Pipeline Smell Detection数学模型的使用方法。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.mathematical_model import (
    MathematicalModel,
    SmellDetectionFramework,
    PipelineGraph,
    OperationNode,
    OperationType,
    ModuleType,
    SmellCategory,
    SeverityLevel
)


def create_demo_pipeline() -> PipelineGraph:
    """创建演示用的Pipeline"""
    print("🔧 创建演示Pipeline...")
    
    # 定义操作节点
    nodes = {
        # 1. 数据加载
        OperationNode(
            node_id="load_data",
            operation_type=OperationType.DATA_LOADING,
            inputs=set(),
            outputs={"df"},
            module_type=ModuleType.DATA_ACQUISITION,
            parameters={"file": "data.csv", "method": "read_csv"},
            line_number=5
        ),
        
        # 2. 数据清洗
        OperationNode(
            node_id="clean_data",
            operation_type=OperationType.DATA_CLEANING,
            inputs={"df"},
            outputs={"df_clean"},
            module_type=ModuleType.DATA_CLEANING,
            parameters={"method": "fillna", "value": 0},
            line_number=8
        ),
        
        # 3. 特征标准化（在划分之前 - 会导致数据泄露）
        OperationNode(
            node_id="scale_features",
            operation_type=OperationType.FEATURE_ENGINEERING,
            inputs={"df_clean"},
            outputs={"df_scaled"},
            module_type=ModuleType.FEATURE_ENGINEERING,
            parameters={"scaler": "StandardScaler.fit"},
            line_number=12
        ),
        
        # 4. 训练测试划分
        OperationNode(
            node_id="split_data",
            operation_type=OperationType.TRAIN_TEST_SPLIT,
            inputs={"df_scaled"},
            outputs={"X_train", "X_test", "y_train", "y_test"},
            module_type=ModuleType.MODEL_OPERATION,
            parameters={"test_size": 0.2},  # 缺少random_state
            line_number=16
        ),
        
        # 5. 模型训练（硬编码参数）
        OperationNode(
            node_id="train_model",
            operation_type=OperationType.MODEL_OPERATION,
            inputs={"X_train", "y_train"},
            outputs={"model"},
            module_type=ModuleType.MODEL_OPERATION,
            parameters={"method": "fit", "n_estimators": 100, "max_depth": 10},
            line_number=20
        ),
        
        # 6. 重复的数据清洗（冗余操作）
        OperationNode(
            node_id="clean_again",
            operation_type=OperationType.DATA_CLEANING,
            inputs={"df_clean"},
            outputs={"df_clean2"},
            module_type=ModuleType.DATA_CLEANING,
            parameters={"method": "fillna", "value": 0},
            line_number=24
        )
    }
    
    # 定义数据依赖边
    edges = {
        ("load_data", "clean_data"),
        ("clean_data", "scale_features"),
        ("scale_features", "split_data"),
        ("split_data", "train_model"),
        ("clean_data", "clean_again")  # 分支
    }
    
    pipeline = PipelineGraph(nodes=nodes, edges=edges, graph=None)
    
    print(f"✅ Pipeline创建完成: {len(nodes)} 个节点, {len(edges)} 条边")
    return pipeline


def demonstrate_basic_analysis(pipeline: PipelineGraph):
    """演示基础分析功能"""
    print("\n📊 基础Pipeline分析")
    print("=" * 50)
    
    model = MathematicalModel()
    
    # 1. 拓扑排序
    topo_order = pipeline.topological_sort()
    print(f"🔄 拓扑排序: {' → '.join(topo_order)}")
    
    # 2. 模块序列
    module_seq = pipeline.module_sequence()
    print(f"📋 模块序列: {' → '.join([m.value for m in module_seq])}")
    
    # 3. Pipeline验证
    validation = model.validate_pipeline(pipeline)
    print(f"✅ Pipeline验证:")
    for key, value in validation.items():
        status = "✅" if value else "❌"
        print(f"   {status} {key}: {value}")
    
    # 4. 复杂度分析
    complexity = model.complexity_analysis(pipeline, 6)
    print(f"⚡ 复杂度分析:")
    print(f"   时间复杂度: {complexity['time_complexity']}")
    print(f"   空间复杂度: {complexity['space_complexity']}")


def demonstrate_smell_detection(pipeline: PipelineGraph):
    """演示Smell检测功能"""
    print("\n🔍 Pipeline Smell检测")
    print("=" * 50)
    
    framework = SmellDetectionFramework()
    
    # 运行检测
    smells = framework.detect_all_smells(pipeline)
    
    if not smells:
        print("🎉 未检测到任何Smell")
        return
    
    print(f"⚠️  检测到 {len(smells)} 个Smell:")
    print()
    
    # 按类别分组显示
    by_category = {}
    for smell in smells:
        category = smell.category.value
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(smell)
    
    for category, category_smells in by_category.items():
        print(f"📂 {category} ({len(category_smells)}个):")
        
        for i, smell in enumerate(category_smells, 1):
            severity_icon = {
                'CRITICAL': '🔴',
                'HIGH': '🟠', 
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }[smell.severity.name]
            
            print(f"   {i}. {severity_icon} {smell.smell_type}")
            print(f"      📍 行号: {smell.line_numbers}")
            print(f"      📝 描述: {smell.description}")
            print(f"      🎯 置信度: {smell.confidence:.2f}")
            print(f"      ⭐ 优先级: {smell.priority():.2f}")
            print(f"      🔗 影响节点: {', '.join(smell.affected_nodes)}")
            print()


def demonstrate_mathematical_functions(pipeline: PipelineGraph):
    """演示数学函数"""
    print("\n🧮 数学函数演示")
    print("=" * 50)
    
    model = MathematicalModel()
    
    # 1. 数据依赖关系
    print("🔗 数据依赖关系:")
    nodes = list(pipeline.nodes)
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            node1, node2 = nodes[i], nodes[j]
            if model.data_dependency(pipeline, node1.node_id, node2.node_id):
                print(f"   {node1.node_id} → {node2.node_id}")
    
    # 2. 执行顺序
    print("\n⏰ 执行顺序:")
    topo_order = pipeline.topological_sort()
    for i, node_id in enumerate(topo_order):
        print(f"   {i+1}. {node_id}")
    
    # 3. 评估指标示例
    print("\n📈 评估指标示例:")
    predicted = {"smell_1", "smell_2", "smell_3"}
    actual = {"smell_2", "smell_3", "smell_4"}
    
    precision = model.precision(predicted, actual)
    recall = model.recall(predicted, actual)
    f1 = model.f1_score(predicted, actual)
    jaccard = model.jaccard_similarity(predicted, actual)
    
    print(f"   精确率: {precision:.3f}")
    print(f"   召回率: {recall:.3f}")
    print(f"   F1分数: {f1:.3f}")
    print(f"   Jaccard相似度: {jaccard:.3f}")
    
    # 4. 统计检验示例
    print("\n📊 统计检验示例:")
    group1 = [0.85, 0.87, 0.89, 0.86, 0.88]  # 方法1的F1分数
    group2 = [0.78, 0.80, 0.82, 0.79, 0.81]  # 方法2的F1分数
    
    cohen_d = model.cohen_d(group1, group2)
    t_stat, p_value = model.paired_t_test(group1, group2)
    
    print(f"   Cohen's d: {cohen_d:.3f}")
    print(f"   t统计量: {t_stat:.3f}")
    print(f"   p值: {p_value:.3f}")
    
    # 解释效应量
    if abs(cohen_d) < 0.2:
        effect_size = "negligible"
    elif abs(cohen_d) < 0.5:
        effect_size = "small"
    elif abs(cohen_d) < 0.8:
        effect_size = "medium"
    else:
        effect_size = "large"
    
    print(f"   效应量: {effect_size}")
    print(f"   显著性: {'是' if p_value < 0.05 else '否'} (α=0.05)")


def demonstrate_statistics(pipeline: PipelineGraph):
    """演示统计分析"""
    print("\n📈 统计分析")
    print("=" * 50)
    
    framework = SmellDetectionFramework()
    smells = framework.detect_all_smells(pipeline)
    
    # 获取统计信息
    stats = framework.get_statistics(smells)
    
    print(f"📊 检测统计:")
    print(f"   总Smell数: {stats['total']}")
    print(f"   平均置信度: {stats['avg_confidence']:.3f}")
    print(f"   平均优先级: {stats['avg_priority']:.3f}")
    
    print(f"\n📂 按类别分布:")
    for category, count in stats['by_category'].items():
        percentage = count / stats['total'] * 100
        print(f"   {category}: {count} ({percentage:.1f}%)")
    
    print(f"\n⚠️  按严重性分布:")
    for severity, count in stats['by_severity'].items():
        percentage = count / stats['total'] * 100
        print(f"   {severity}: {count} ({percentage:.1f}%)")


def demonstrate_custom_detector():
    """演示自定义检测器"""
    print("\n🔧 自定义检测器演示")
    print("=" * 50)
    
    def custom_long_pipeline_detector(pipeline: PipelineGraph):
        """自定义检测器：检测过长的Pipeline"""
        from src.core.mathematical_model import SmellInstance
        
        if len(pipeline.nodes) > 5:
            return [SmellInstance(
                smell_type="LONG_PIPELINE",
                category=SmellCategory.STRUCTURE,
                severity=SeverityLevel.LOW,
                affected_nodes=set(node.node_id for node in pipeline.nodes),
                description=f"Pipeline过长，包含{len(pipeline.nodes)}个节点",
                confidence=0.8,
                line_numbers=[node.line_number for node in pipeline.nodes]
            )]
        return []
    
    # 注册自定义检测器
    framework = SmellDetectionFramework()
    framework.register_detector("LONG_PIPELINE", custom_long_pipeline_detector)
    
    print("✅ 已注册自定义检测器: LONG_PIPELINE")
    print(f"📊 当前检测器数量: {len(framework.detectors)}")
    
    # 测试自定义检测器
    pipeline = create_demo_pipeline()
    smells = framework.detect_all_smells(pipeline)
    
    custom_smells = [s for s in smells if s.smell_type == "LONG_PIPELINE"]
    if custom_smells:
        print(f"🎯 自定义检测器检测到: {len(custom_smells)} 个LONG_PIPELINE")
    else:
        print("ℹ️  自定义检测器未检测到LONG_PIPELINE")


def main():
    """主函数"""
    print("🚀 Pipeline Smell Detection 数学模型演示")
    print("=" * 60)
    
    # 创建演示Pipeline
    pipeline = create_demo_pipeline()
    
    # 演示各种功能
    demonstrate_basic_analysis(pipeline)
    demonstrate_smell_detection(pipeline)
    demonstrate_mathematical_functions(pipeline)
    demonstrate_statistics(pipeline)
    demonstrate_custom_detector()
    
    print("\n🎉 演示完成!")
    print("\n📚 更多信息请参考:")
    print("   - docs/MATHEMATICAL_MODEL.md - 完整数学定义")
    print("   - tests/test_mathematical_model.py - 测试用例")
    print("   - src/core/mathematical_model.py - 实现代码")


if __name__ == '__main__':
    main()