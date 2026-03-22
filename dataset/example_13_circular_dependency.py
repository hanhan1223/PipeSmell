"""
机器学习Pipeline示例 - 循环依赖
包含CIRCULAR_DEPENDENCY Smell: 模块间的循环依赖关系
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# 模拟循环依赖的数据处理流程
def process_data_a(data):
    """处理步骤A"""
    result = data.copy()
    result['feature_a'] = result['feature_b'] * 2  # 依赖feature_b
    return result

def process_data_b(data):
    """处理步骤B"""
    result = data.copy()
    result['feature_b'] = result['feature_a'] / 2  # 依赖feature_a，形成循环
    return result

# 加载数据
df = pd.read_csv('circular_data.csv')

# ❌ CIRCULAR_DEPENDENCY: 两个处理函数互相依赖
# 在实际复杂Pipeline中可能出现这种循环引用
df = process_data_a(df)
df = process_data_b(df)  # 这会导致不确定的结果

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = RandomForestClassifier(random_state=42)
model.fit(X_train_scaled, y_train)
