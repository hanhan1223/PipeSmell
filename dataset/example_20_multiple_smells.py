"""
机器学习Pipeline示例 - 多种Smell混合
包含多个Smell: DATA_LEAKAGE, MISSING_RANDOM_SEED, MISSING_EVALUATION, HARDCODED_PARAMETERS
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import LogisticRegression

# 加载数据
df = pd.read_csv('data.csv')
X = df.drop('target', axis=1)
y = df['target']

# ❌ SMELL 1: DATA_LEAKAGE - 在划分前标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # 在全部数据上fit

# ❌ SMELL 2: MISSING_RANDOM_SEED - 未设置random_state
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3)

# ❌ SMELL 3: HARDCODED_PARAMETERS - 硬编码参数
model = LogisticRegression(
    C=1.0,              # 硬编码
    max_iter=100,       # 硬编码
    solver='lbfgs',     # 硬编码
    random_state=42     # 硬编码
)

model.fit(X_train, y_train)

# ❌ SMELL 4: MISSING_EVALUATION - 没有评估步骤
predictions = model.predict(X_test)
# 缺少 accuracy_score 或其他评估指标
print("Predictions done")
