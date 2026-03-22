"""Fit on all rows then report accuracy (single split not used)."""

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

df = pd.read_csv("data.csv")
X = df.drop(columns=["target"])
y = df["target"]

m = LogisticRegression(max_iter=300, random_state=42)
m.fit(X, y)
print(accuracy_score(y, m.predict(X)))
