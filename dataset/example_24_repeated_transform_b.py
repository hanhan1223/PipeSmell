"""
机器学习Pipeline示例 - 重复转换（变体B）
包含REPEATED_TRANSFORM Smell: 对同一数据链使用多种缩放器
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.linear_model import Ridge

# 加载数据
df = pd.read_csv('prices_b.csv')
X = df.drop('price', axis=1)
y = df['price']

# 划分数据
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ❌ REPEATED_TRANSFORM: 连续两次缩放
scaler1 = RobustScaler()
X_train_scaled = scaler1.fit_transform(X_train)

scaler2 = StandardScaler()  # 第二次缩放
X_train_scaled2 = scaler2.fit_transform(X_train_scaled)

# 训练模型
model = Ridge()
model.fit(X_train_scaled2, y_train)
