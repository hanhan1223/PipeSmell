"""
机器学习Pipeline示例 - 硬编码参数（变体B）
包含HARDCODED_PARAMETERS Smell: 超参数直接写死在代码中
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score

# 加载数据
df = pd.read_csv('digits_b.csv')
X = df.drop('class', axis=1)
y = df['class']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ❌ HARDCODED_PARAMETERS: 所有参数都是硬编码的
model = GradientBoostingClassifier(
    n_estimators=200,    # 硬编码
    learning_rate=0.05,  # 硬编码
    max_depth=4,         # 硬编码
    min_samples_split=4, # 硬编码
    random_state=42      # 硬编码
)

model.fit(X_train, y_train)
predictions = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, predictions)}")
