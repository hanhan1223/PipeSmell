"""
机器学习Pipeline示例 - 缺少版本控制
包含LACK_OF_VERSION_CONTROL Smell: 没有requirements.txt记录依赖版本
"""

# ❌ LACK_OF_VERSION_CONTROL: 没有requirements.txt
# 这会导致代码无法复现，因为依赖版本不确定

import pandas as pd
# 注意：没有记录pandas版本

import numpy as np
# 注意：没有记录numpy版本

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
# 注意：没有记录scikit-learn版本

# 加载数据
df = pd.read_csv('data.csv')
X = df.drop('target', axis=1)
y = df['target']

# 划分数据
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

# 训练模型
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# 预测和评估
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"Model accuracy: {accuracy}")

# 应该有的requirements.txt内容（但缺失了）:
# pandas==1.5.0
# numpy==1.23.0
# scikit-learn==1.2.0
