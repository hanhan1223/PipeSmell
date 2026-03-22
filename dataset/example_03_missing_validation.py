"""
机器学习Pipeline示例 - 缺少验证集
包含MISSING_VALIDATION Smell: 没有划分验证集，直接在训练数据上评估
"""

import pandas as pd
from sklearn.svm import SVC
from sklearn.metrics import classification_report

# 加载数据
data = pd.read_csv('classification_data.csv')
X = data.drop('label', axis=1)
y = data['label']

# ❌ MISSING_VALIDATION: 没有train_test_split，直接在全部数据上训练和评估
model = SVC()
model.fit(X, y)  # 在全部数据上训练

# ❌ 在训练数据上评估，无法评估泛化能力
predictions = model.predict(X)
print(classification_report(y, predictions))
