"""
机器学习Pipeline示例 - 缺少模型评估（变体B）
包含MISSING_EVALUATION Smell: 有训练但没有评估步骤
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import ExtraTreesClassifier

# 加载数据
data = pd.read_csv('churn_b.csv')
X = data.drop('churn', axis=1)
y = data['churn']

# 划分数据
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# 训练模型
clf = ExtraTreesClassifier()
clf.fit(X_train, y_train)

# ❌ MISSING_EVALUATION: 没有调用score()或任何评估指标
# 模型训练完成但没有评估步骤

# 只有预测，没有评估
predictions = clf.predict(X_test)
print("Predictions generated")
