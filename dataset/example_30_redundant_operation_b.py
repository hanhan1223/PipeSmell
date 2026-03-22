"""
机器学习Pipeline示例 - 冗余操作（变体B）
包含REDUNDANT_OPERATION Smell: 操作效果互相抵消
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import ElasticNet

# 加载数据
df = pd.read_csv('sparse_b.csv')

# ❌ REDUNDANT_OPERATION: dropna后立即fillna，操作互相抵消
df_cleaned = df.dropna()  # 删除所有缺失值
df_filled = df_cleaned.fillna(0)  # 在已经没有缺失值的数据上fillna，多余操作

X = df_cleaned.drop('target', axis=1)
y = df_cleaned['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = ElasticNet()
model.fit(X_train, y_train)
