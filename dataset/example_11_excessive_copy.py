"""
机器学习Pipeline示例 - 过度复制
包含EXCESSIVE_COPY Smell: 不必要的数据复制
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier

# 加载数据
df = pd.read_csv('dataset.csv')

# ❌ EXCESSIVE_COPY: 不必要的数据复制
# 后续操作不会修改原始数据，不需要复制
df_copy1 = df.copy()
df_copy2 = df_copy1.copy()  # 再次复制，完全多余
df_copy3 = df_copy2.copy()  # 第三次复制

X = df_copy3.drop('label', axis=1)
y = df_copy3['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = KNeighborsClassifier()
model.fit(X_train_scaled, y_train)
