"""Save each preprocessing stage to disk for debugging."""

import pandas as pd

df = pd.read_csv("raw.csv")
df = df.dropna()
df.to_csv("stage1.csv", index=False)
df = df.fillna(0)
df.to_csv("stage2.csv", index=False)
df["x"] = df["x"].astype(float)
df.to_csv("stage3.csv", index=False)
df.to_csv("final.csv", index=False)
