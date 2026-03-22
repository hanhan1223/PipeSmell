"""
机器学习Pipeline示例 - 低效聚合
包含INEFFICIENT_AGGREGATION Smell: 循环逐行聚合而非向量化操作
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier

# 加载数据
df = pd.read_csv('sales_data.csv')

# ❌ INEFFICIENT_AGGREGATION: 使用循环逐行计算，而非向量化操作
mean_values = []
for idx in range(len(df)):
    row_mean = df.iloc[idx].mean()  # 逐行计算，效率低下
    mean_values.append(row_mean)

df['row_mean'] = mean_values

# 正确的做法应该是:
# df['row_mean'] = df.mean(axis=1)  # 向量化操作

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = GradientBoostingClassifier()
model.fit(X_train, y_train)
