"""
机器学习Pipeline示例 - 数据泄露问题
包含DATA_LEAKAGE Smell: 在train_test_split之前对整个数据集执行标准化
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# 加载数据
data = pd.read_csv('data.csv')
X = data.drop('target', axis=1)
y = data['target']

# ❌ DATA_LEAKAGE: 在划分前对整个数据集进行标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # 这里泄露了测试集信息！

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2)

# 训练模型
model = LogisticRegression()
model.fit(X_train, y_train)

# 预测和评估
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy}")
