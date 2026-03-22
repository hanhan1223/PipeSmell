"""Row-wise stats before fitting a tree model."""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier

df = pd.read_csv("sales.csv")

mean_values = []
for idx in range(len(df)):
    row_mean = df.iloc[idx].mean()
    mean_values.append(row_mean)

df = df.assign(row_mean=mean_values)
X = df.drop(columns=["target"])
y = df["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
GradientBoostingClassifier(random_state=42).fit(X_train, y_train)
