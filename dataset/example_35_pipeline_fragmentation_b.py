"""
机器学习Pipeline示例 - Pipeline碎片化（变体B）
包含PIPELINE_FRAGMENTATION Smell: 包含大量短小的操作链
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

# 加载数据
df = pd.read_csv('wide_b.csv')

# ❌ PIPELINE_FRAGMENTATION: 大量短小的操作链
df = df.drop('c1', axis=1)
df = df.drop('c2', axis=1)
df = df.drop('c3', axis=1)
df['c4'] = df['c4'].fillna(0)
df['c5'] = df['c5'].fillna(0)
df['c6'] = df['c6'].astype(float)
df['c7'] = df['c7'].astype(int)
df = df.rename(columns={'c8': 'f8'})
df = df.rename(columns={'c9': 'f9'})
df = df.rename(columns={'c10': 'f10'})
df = df.drop('c11', axis=1)

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = LogisticRegression()
model.fit(X_train_scaled, y_train)
