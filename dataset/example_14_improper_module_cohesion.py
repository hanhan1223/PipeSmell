"""
机器学习Pipeline示例 - 模块内聚不当
包含IMPROPER_MODULE_COHESION Smell: 模块包含多种不同类型的操作
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt

# 加载数据
df = pd.read_csv('mixed_data.csv')

# ❌ IMPROPER_MODULE_COHESION: 一个代码块包含多种不相关操作
# 数据清洗、可视化、模型训练、参数调优都混在一起

# 数据预处理
df = df.dropna()
df['category'] = LabelEncoder().fit_transform(df['category'])

# 数据可视化（不应该和训练混在一起）
plt.figure(figsize=(10, 6))
plt.hist(df['feature1'], bins=30)
plt.title('Feature Distribution')
plt.savefig('feature_dist.png')

# 特征工程
X = df.drop('target', axis=1)
y = df['target']

# 数据分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

# 模型训练
model = RandomForestClassifier()

# 参数调优（不应该和主流程混在一起）
param_grid = {'n_estimators': [50, 100, 200], 'max_depth': [5, 10, None]}
grid_search = GridSearchCV(model, param_grid, cv=5)
grid_search.fit(X_train_scaled, y_train)

# 评估
best_model = grid_search.best_estimator_
predictions = best_model.predict(X_test)
print(classification_report(y_test, predictions))
