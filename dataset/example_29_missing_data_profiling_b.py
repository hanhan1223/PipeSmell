"""
机器学习Pipeline示例 - 缺少数据探索（变体B）
包含MISSING_DATA_PROFILING Smell: 没有head/describe等数据探索操作
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# 加载数据
# ❌ MISSING_DATA_PROFILING: 直接加载数据，没有进行任何数据探索
df = pd.read_csv('raw_unknown_b.csv')

# 应该有的数据探索步骤（但缺失了）:
# print(df.head())
# print(df.describe())

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = RandomForestClassifier()
model.fit(X_train_scaled, y_train)

predictions = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, predictions)}")
