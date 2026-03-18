"""
测试Bug修复

验证核心Bug是否已修复。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.core.pipeline import PipelineGraph, PipelineExtractor
from src.smells.detector import DetectorRegistry
from src.core.parser import ASTParser


def test_pipeline_graph_has_file_path():
    """测试PipelineGraph是否有file_path属性"""
    pipeline = PipelineGraph(file_path="test.py")
    assert hasattr(pipeline, 'file_path')
    assert pipeline.file_path == "test.py"


def test_pipeline_graph_has_get_nodes():
    """测试PipelineGraph是否有get_nodes方法"""
    pipeline = PipelineGraph()
    assert hasattr(pipeline, 'get_nodes')
    assert callable(pipeline.get_nodes)
    
    nodes = pipeline.get_nodes()
    assert isinstance(nodes, list)


def test_pipeline_graph_has_get_num_edges():
    """测试PipelineGraph是否有get_num_edges方法"""
    pipeline = PipelineGraph()
    assert hasattr(pipeline, 'get_num_edges')
    assert callable(pipeline.get_num_edges)
    
    num_edges = pipeline.get_num_edges()
    assert isinstance(num_edges, int)
    assert num_edges >= 0


def test_pipeline_graph_has_get_num_nodes():
    """测试PipelineGraph是否有get_num_nodes方法"""
    pipeline = PipelineGraph()
    assert hasattr(pipeline, 'get_num_nodes')
    assert callable(pipeline.get_num_nodes)
    
    num_nodes = pipeline.get_num_nodes()
    assert isinstance(num_nodes, int)
    assert num_nodes >= 0


def test_ast_parser_returns_ast_result():
    """测试ASTParser.parse_file返回ASTResult对象"""
    parser = ASTParser()
    
    # 创建临时测试文件
    test_file = Path("test_temp.py")
    test_file.write_text("import pandas as pd\ndf = pd.read_csv('data.csv')\n")
    
    try:
        result = parser.parse_file(str(test_file))
        
        assert result is not None
        assert hasattr(result, 'ast_tree')
        assert hasattr(result, 'api_calls')
        assert isinstance(result.api_calls, list)
    finally:
        test_file.unlink()


def test_pipeline_extractor_integration():
    """测试PipelineExtractor完整流程"""
    # 创建测试文件
    test_file = Path("test_pipeline.py")
    test_code = """
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv('data.csv')
df = df.fillna(0)
X = df.drop('target', axis=1)
y = df['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)
"""
    test_file.write_text(test_code)
    
    try:
        extractor = PipelineExtractor()
        pipeline = extractor.extract_from_file(str(test_file))
        
        assert pipeline is not None
        assert hasattr(pipeline, 'file_path')
        assert pipeline.file_path == str(test_file)
        
        # 测试新增的方法
        nodes = pipeline.get_nodes()
        assert isinstance(nodes, list)
        
        num_edges = pipeline.get_num_edges()
        assert isinstance(num_edges, int)
        
        num_nodes = pipeline.get_num_nodes()
        assert isinstance(num_nodes, int)
        assert num_nodes == len(nodes)
        
    finally:
        test_file.unlink()


def test_detector_registry_integration():
    """测试DetectorRegistry与修复后的Pipeline集成"""
    # 创建测试文件
    test_file = Path("test_detector.py")
    test_code = """
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

df = pd.read_csv('data.csv')

# DATA LEAKAGE
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df)

X_train, X_test, y_train, y_test = train_test_split(df_scaled, df['target'])
"""
    test_file.write_text(test_code, encoding='utf-8')
    
    try:
        extractor = PipelineExtractor()
        pipeline = extractor.extract_from_file(str(test_file))
        
        assert pipeline is not None
        
        registry = DetectorRegistry()
        result = registry.detect_all(pipeline)
        
        # 验证结果结构
        assert hasattr(result, 'pipeline_info')
        assert hasattr(result, 'detected_smells')
        assert hasattr(result, 'runtime_ms')
        
        # 验证pipeline_info包含必要字段
        assert 'file_path' in result.pipeline_info
        assert 'num_nodes' in result.pipeline_info
        assert 'num_edges' in result.pipeline_info
        
    finally:
        test_file.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
