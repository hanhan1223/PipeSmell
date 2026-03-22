"""
机器学习Pipeline示例 - 大DataFrame操作
包含LARGE_DATA_FRAME_OPERATION Smell: 对大DataFrame的全量遍历
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.naive_bayes import GaussianNB

# 加载大数据集
df = pd.read_csv('very_large_dataset.csv')  # 假设有100万行

# ❌ LARGE_DATA_FRAME_OPERATION: 对大DataFrame进行逐行遍历
# 效率极低，应该使用向量化操作

# 错误的做法：逐行遍历
new_values = []
for index, row in df.iterrows():  # iterrows()在大数据上很慢
    calculated_value = row['feature1'] * 2 + row['feature2'] / 2
    new_values.append(calculated_value)

df['calculated'] = new_values

# 正确的做法应该是：
# df['calculated'] = df['feature1'] * 2 + df['feature2'] / 2

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = GaussianNB()
model.fit(X_train_scaled, y_train)
