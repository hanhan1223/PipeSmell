"""
机器学习Pipeline示例 - 重复转换
包含REPEATED_TRANSFORM Smell: 对同一列进行多次相同类型的转换
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import LinearRegression

# 加载数据
df = pd.read_csv('housing.csv')
X = df.drop('price', axis=1)
y = df['price']

# 划分数据
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ❌ REPEATED_TRANSFORM: 对同一数据进行两次标准化
scaler1 = StandardScaler()
X_train_scaled = scaler1.fit_transform(X_train)

scaler2 = MinMaxScaler()  # 重复的标准化操作
X_train_scaled2 = scaler2.fit_transform(X_train_scaled)

# 训练模型
model = LinearRegression()
model.fit(X_train_scaled2, y_train)
