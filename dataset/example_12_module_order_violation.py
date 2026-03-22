"""
机器学习Pipeline示例 - 模块顺序违反
包含MODULE_ORDER_VIOLATION Smell: 模块顺序不符合预期
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression

# 加载数据
df = pd.read_csv('high_dim_data.csv')
X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ❌ MODULE_ORDER_VIOLATION: 特征选择应该在标准化之前
# 但这里先标准化再特征选择，顺序不是最优
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 特征选择应该在标准化之前进行
selector = SelectKBest(score_func=f_classif, k=10)
X_train_selected = selector.fit_transform(X_train_scaled, y_train)
X_test_selected = selector.transform(X_test_scaled)

model = LogisticRegression()
model.fit(X_train_selected, y_train)
