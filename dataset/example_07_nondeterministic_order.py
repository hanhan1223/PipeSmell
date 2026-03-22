"""
机器学习Pipeline示例 - 非确定性顺序
包含NON_DETERMINISTIC_ORDER Smell: 使用set/dict的无序迭代
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

# 加载数据
df = pd.read_csv('features.csv')

# ❌ NON_DETERMINISTIC_ORDER: 使用set存储列名，迭代顺序不确定
feature_set = {'feature_a', 'feature_b', 'feature_c', 'feature_d'}
selected_features = list(feature_set)  # set的迭代顺序不确定

X = df[selected_features]
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = LogisticRegression()
model.fit(X_train_scaled, y_train)
