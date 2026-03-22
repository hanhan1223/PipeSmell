"""High-dimensional baseline with scaling and univariate screening."""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression

df = pd.read_csv("high_dim.csv")
X = df.drop(columns=["target"])
y = df["target"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

scaler = StandardScaler()
Xt_tr = scaler.fit_transform(X_train)
Xt_te = scaler.transform(X_test)

selector = SelectKBest(score_func=f_classif, k=10)
X_sel_tr = selector.fit_transform(Xt_tr, y_train)
X_sel_te = selector.transform(Xt_te)

LogisticRegression(max_iter=500, random_state=42).fit(X_sel_tr, y_train)
