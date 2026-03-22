"""
机器学习Pipeline示例 - 缺少随机种子
包含MISSING_RANDOM_SEED Smell: train_test_split未设置random_state
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# 加载数据
df = pd.read_csv('dataset.csv')
X = df.iloc[:, :-1]
y = df.iloc[:, -1]

# ❌ MISSING_RANDOM_SEED: 未设置random_state，结果不可复现
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)

# 训练模型
clf = RandomForestClassifier()
clf.fit(X_train, y_train)

# 评估
predictions = clf.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, predictions)}")
