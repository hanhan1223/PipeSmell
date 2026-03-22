"""
机器学习Pipeline示例 - Pipeline碎片化
包含PIPELINE_FRAGMENTATION Smell: 包含大量短小的操作链
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

# 加载数据
df = pd.read_csv('data.csv')

# ❌ PIPELINE_FRAGMENTATION: 大量短小的操作链
# 每个操作都单独一行，没有组合成有意义的步骤

# 步骤1: 删除一列
df = df.drop('col1', axis=1)

# 步骤2: 删除另一列
df = df.drop('col2', axis=1)

# 步骤3: 再删除一列
df = df.drop('col3', axis=1)

# 步骤4: 填充缺失值
df['col4'] = df['col4'].fillna(0)

# 步骤5: 再填充另一列
df['col5'] = df['col5'].fillna(0)

# 步骤6: 类型转换
df['col6'] = df['col6'].astype(float)

# 步骤7: 再转换
df['col7'] = df['col7'].astype(int)

# 步骤8: 重命名
df = df.rename(columns={'col8': 'feature8'})

# 步骤9: 再重命名
df = df.rename(columns={'col9': 'feature9'})

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = LogisticRegression()
model.fit(X_train_scaled, y_train)
