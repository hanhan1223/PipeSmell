"""
机器学习Pipeline示例 - 大DataFrame操作（变体B）
包含LARGE_DATA_FRAME_OPERATION Smell: 对大DataFrame的全量遍历
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import SGDClassifier

# 加载大数据集
df = pd.read_csv('huge_b.csv')

# ❌ LARGE_DATA_FRAME_OPERATION: 对大DataFrame进行逐行遍历
vals = []
for index, row in df.iterrows():
    vals.append(row['x1'] * 3 + row['x2'])

df['combo'] = vals

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = SGDClassifier(random_state=42)
model.fit(X_train_scaled, y_train)
