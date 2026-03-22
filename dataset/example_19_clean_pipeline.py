"""
机器学习Pipeline示例 - 干净的Pipeline（无Smell）
这是一个正确的Pipeline示例，用于对比测试
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# 加载数据
df = pd.read_csv('data.csv')

# 数据探索（好的实践）
print("Data shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())
print("\nData description:")
print(df.describe())
print("\nMissing values:")
print(df.isnull().sum())

# 分离特征和标签
X = df.drop('target', axis=1)
y = df['target']

# 划分训练集和测试集（设置random_state保证可复现）
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 标准化（在划分后进行，避免数据泄露）
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 训练模型
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# 模型评估
y_pred = model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
print(f"\nModel Accuracy: {accuracy:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))
