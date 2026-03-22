"""
机器学习Pipeline示例 - 非确定性顺序（变体B）
包含NON_DETERMINISTIC_ORDER Smell: 使用dict键的无序迭代
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

# 加载数据
df = pd.read_csv('features_b.csv')

# ❌ NON_DETERMINISTIC_ORDER: 将dict的键转为list，顺序不确定
feature_dict = {'feat_a': 0, 'feat_b': 1, 'feat_c': 2, 'feat_d': 3}
selected_features = list(feature_dict.keys())  # dict键在Python3.7+有序但此处仍被检测为风险模式

X = df[selected_features]
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = LogisticRegression()
model.fit(X_train_scaled, y_train)
