"""Trying both normalizations to see which works better."""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import LogisticRegression

df = pd.read_csv("features.csv")
X = df.drop(columns=["label"])
y = df["label"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=0
)

s1 = StandardScaler()
X1 = s1.fit_transform(X_train)
s2 = MinMaxScaler()
X2 = s2.fit_transform(X1)

clf = LogisticRegression(max_iter=400, random_state=0)
clf.fit(X2, y_train)
