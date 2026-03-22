"""
机器学习Pipeline示例 - 不必要的物化（变体B）
包含UNNECESSARY_MATERIALIZATION Smell: 频繁的中间结果保存
"""

import pandas as pd
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import AdaBoostClassifier

# 加载数据
df = pd.read_csv('large_dataset_b.csv')

# ❌ UNNECESSARY_MATERIALIZATION: 频繁保存中间结果
# 创建临时目录保存中间文件
os.makedirs('temp_data_b', exist_ok=True)

# 步骤1: 保存原始数据
df.to_csv('temp_data_b/step1_raw.csv', index=False)

# 步骤2: 删除缺失值
df_clean = df.dropna()
df_clean.to_csv('temp_data_b/step2_cleaned.csv', index=False)  # 不必要的保存

# 步骤3: 特征选择
df_selected = df_clean[['feature1', 'feature2', 'feature3', 'target']]
df_selected.to_csv('temp_data_b/step3_selected.csv', index=False)  # 不必要的保存

# 步骤4: 类型转换
df_selected['feature1'] = df_selected['feature1'].astype(float)
df_selected.to_csv('temp_data_b/step4_converted.csv', index=False)  # 不必要的保存

X = df_selected.drop('target', axis=1)
y = df_selected['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = AdaBoostClassifier(random_state=42)
model.fit(X_train_scaled, y_train)
