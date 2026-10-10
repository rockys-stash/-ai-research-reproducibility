"""Bootstrap interval of the class-0 minus class-1 mean alcohol in wine; uses pandas, which is not declared."""
import json

import numpy as np
import pandas as pd
from sklearn.datasets import load_wine

data = load_wine(as_frame=True)
df: pd.DataFrame = data.frame
a = df.loc[df["target"] == 0, "alcohol"].to_numpy()
b = df.loc[df["target"] == 1, "alcohol"].to_numpy()
rng = np.random.default_rng(0)
diffs = [rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean() for _ in range(2000)]
results = {"mean_difference": float(a.mean() - b.mean()), "ci_low": float(np.percentile(diffs, 2.5)),
           "ci_high": float(np.percentile(diffs, 97.5))}
with open("results.json", "w") as f:
    json.dump(results, f, indent=1)
print(results)
