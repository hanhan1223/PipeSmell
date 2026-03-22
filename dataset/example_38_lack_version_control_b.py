"""
机器学习Pipeline示例 - 缺少版本控制（变体B）
包含LACK_OF_VERSION_CONTROL Smell: 没有requirements.txt记录依赖版本
"""

# ❌ LACK_OF_VERSION_CONTROL: 没有requirements.txt

import pandas as pd
# 注意：没有记录pandas版本

import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# 加载数据
df = pd.read_csv('data_b2.csv')
X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = LogisticRegression(max_iter=200)
model.fit(X_train_scaled, y_train)

predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"Model accuracy: {accuracy}")
