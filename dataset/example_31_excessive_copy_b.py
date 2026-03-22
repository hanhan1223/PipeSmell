"""
机器学习Pipeline示例 - 过度复制（变体B）
包含EXCESSIVE_COPY Smell: 不必要的数据复制
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# 加载数据
df = pd.read_csv('tabular_b2.csv')

# ❌ EXCESSIVE_COPY: 不必要的数据复制
# 后续操作不会修改原始数据，不需要复制
df_work = df.copy()
df_work = df_work.copy()
df_work = df_work.copy()

X = df_work.drop('label', axis=1)
y = df_work['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = DecisionTreeClassifier()
model.fit(X_train_scaled, y_train)
