"""Feature list from unique column names (order not guaranteed)."""

import pandas as pd

df = pd.read_csv("wide_table.csv")
raw = {"a", "b", "c", "d"}
cols = list(raw)
use = [c for c in cols if c in df.columns]
print(df[use].head())
