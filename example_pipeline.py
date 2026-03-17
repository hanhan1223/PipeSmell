"""
示例Pipeline文件 - 包含多种Pipeline Smell

这是一个故意包含多种Pipeline Smell的示例代码，
用于测试和演示Pipeline Smell Detection系统。
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


# ============== Smell Category 1: ORDER ==============

# Smell 1.1: DATA LEAKAGE (CRITICAL)
# 在train_test_split之前对整个数据集进行标准化，导致数据泄露
def pipeline_with_data_leakage():
    """错误示例：数据泄露问题"""
    
    # 读取数据
    df = pd.read_csv('data.csv')
    
    # ❌ DATA LEAKAGE: 在划分训练/测试集之前进行标准化
    scaler = StandardScaler()
    df_normalized = pd.DataFrame(
        scaler.fit_transform(df),
        columns=df.columns
    )
    
    # 划分训练/测试集
    X = df_normalized.drop('target', axis=1)
    y = df_normalized['target']
    
    # ❌ MISSING RANDOM SEED：未设置random_state
    X_train, X_test, y_train, y_test = train_test_split(X, y)
    
    # 训练模型
    model = RandomForestClassifier(
        # ❌ HARDCODED PARAMETERS: 硬编码超参数
        n_estimators=100,
        max_depth=10
    )
    model.fit(X_train, y_train)
    
    # ❌ MISSING EVALUATION: 缺少模型评估步骤
    predictions = model.predict(X_test)


# ============== Smell Category 2: REDUNDANCY ==============

def pipeline_with_redundancy():
    """错误示例：冗余操作"""
    
    df = pd.read_csv('data.csv')
    
    # ❌ REDUNDANT OPERATION: 先dropna再fillna
    df = df.dropna()
    df = df.fillna(0)
    
    # ❌ REPEATED TRANSFORM: 对同一列重复进行标准化
    scaler1 = StandardScaler()
    df['feature1'] = scaler1.fit_transform(df[['feature1']])
    
    scaler2 = StandardScaler()
    df['feature1'] = scaler2.fit_transform(df[['feature1']])
    
    # ❌ EXCESSIVE COPY: 不必要的数据复制
    df_copy1 = df.copy()
    df_copy2 = df_copy1.copy()
    df_copy3 = df_copy2.copy()
    
    # train_test_split
    X = df_copy3.drop('target', axis=1)
    y = df_copy3['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)
    
    model = RandomForestClassifier()
    model.fit(X_train, y_train)


# ============== Smell Category 3: MISSING ==============

def pipeline_with_missing_operations():
    """错误示例：缺少必要操作"""
    
    # ❌ MISSING DATA PROFILING: 没有数据探索分析
    # 没有 df.head(), df.describe(), df.info() 等操作
    
    df = pd.read_csv('data.csv')
    
    # ❌ MISSING VALIDATION: 只有训练/测试集，没有验证集
    X = df.drop('target', axis=1)
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)
    
    model = RandomForestClassifier()
    model.fit(X_train, y_train)


# ============== Smell Category 4: PERFORMANCE ==============

def pipeline_with_performance_issues():
    """错误示例：性能问题"""
    
    df = pd.read_csv('large_dataset.csv')
    
    # ❌ INEFFICIENT AGGREGATION: 使用for循环逐行聚合
    result = 0
    for idx, row in df.iterrows():
        result += row['value']
    
    # ❌ UNNECESSARY MATERIALIZATION: 频繁的中间结果持久化
    df.to_csv('temp_step1.csv')
    df = pd.read_csv('temp_step1.csv')
    df.to_csv('temp_step2.csv')
    df = pd.read_csv('temp_step2.csv')
    df.to_csv('temp_step3.csv')
    df = pd.read_csv('temp_step3.csv')
    
    # ❌ LARGE DATAFRAME OPERATION: 对大DataFrame的全量操作
    for row in df.itertuples():
        # 处理每一行
        pass


# ============== Smell Category 5: STRUCTURE ==============

def pipeline_with_structure_issues():
    """错误示例：结构问题"""
    
    df = pd.read_csv('data.csv')
    
    # ❌ IMPROPER MODULE COHESION: 模块内聚性差
    # 同一个函数中混合了数据清洗、特征工程和模型训练
    
    # 数据清洗
    df = df.dropna()
    df['feature1'] = df['feature1'].fillna(0)
    
    # 特征工程
    df['new_feature'] = df['feature1'] * df['feature2']
    df['feature1_scaled'] = (df['feature1'] - df['feature1'].mean()) / df['feature1'].std()
    
    # 模型训练
    X = df.drop('target', axis=1)
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 数据清洗（再次，导致模块不一致）
    df_test = X_test.copy()
    df_test = df_test.dropna()


# ============== Smell Category 6: REPRODUCIBILITY ==============

def pipeline_with_reproducibility_issues():
    """错误示例：可复现性问题"""
    
    # ❌ NON_DETERMINISTIC ORDER: 使用set的无序迭代
    categories = set(['A', 'B', 'C'])
    for category in categories:
        # 结果可能每次运行都不同
        print(category)
    
    df = pd.read_csv('data.csv')
    
    # ❌ LACK OF VERSION CONTROL: 项目没有requirements.txt
    # （假设这个文件所在目录没有requirements.txt）
    
    # ❌ HARDCODED PARAMETERS: 硬编码路径和参数
    train_data_path = "C:/Users/13763/Desktop/data/train.csv"
    test_data_path = "C:/Users/13763/Desktop/data/test.csv"
    
    X = df.drop('target', axis=1)
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)
    
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=2,
        min_samples_leaf=1
    )
    model.fit(X_train, y_train)


# ============== Correct Example (Reference) ==============

def correct_pipeline():
    """正确示例：无Pipeline Smell的参考实现"""
    
    # 1. 数据探索 (MISSING DATA PROFILING - 已解决)
    df = pd.read_csv('data.csv')
    print(df.head())
    print(df.describe())
    print(df.info())
    
    # 2. 数据清洗
    df_cleaned = df.dropna()
    
    # 3. 划分训练/测试集 (DATA LEAKAGE - 已解决)
    X = df_cleaned.drop('target', axis=1)
    y = df_cleaned['target']
    
    # 设置随机种子 (MISSING RANDOM SEED - 已解决)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=0.2,
        random_state=42
    )
    
    # 4. 标准化（只在训练集上fit）
    scaler = StandardScaler()
    X_train_normalized = scaler.fit_transform(X_train)
    X_test_normalized = scaler.transform(X_test)
    
    # 5. 模型配置（不硬编码）
    model_params = {
        'n_estimators': 100,
        'max_depth': 10,
        'random_state': 42
    }
    
    model = RandomForestClassifier(**model_params)
    model.fit(X_train_normalized, y_train)
    
    # 6. 模型评估 (MISSING EVALUATION - 已解决)
    predictions = model.predict(X_test_normalized)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Model Accuracy: {accuracy:.4f}")


if __name__ == '__main__':
    print("Testing Pipeline Smell Detection")
    print("=" * 50)
    
    # 运行包含Smell的示例
    print("\n1. Pipeline with Data Leakage:")
    pipeline_with_data_leakage()
    
    print("\n2. Pipeline with Redundancy:")
    pipeline_with_redundancy()
    
    print("\n3. Pipeline with Missing Operations:")
    pipeline_with_missing_operations()
    
    print("\n4. Pipeline with Performance Issues:")
    pipeline_with_performance_issues()
    
    print("\n5. Pipeline with Structure Issues:")
    pipeline_with_structure_issues()
    
    print("\n6. Pipeline with Reproducibility Issues:")
    pipeline_with_reproducibility_issues()
    
    print("\n7. Correct Pipeline (Reference):")
    correct_pipeline()
