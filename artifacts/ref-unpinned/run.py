"""Ridge with and without degree-2 polynomial features on diabetes; 5-fold CV (deterministic folds)."""
import json

import numpy as np
from sklearn.datasets import load_diabetes
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

X, y = load_diabetes(return_X_y=True)
cv = KFold(n_splits=5, shuffle=True, random_state=0)
base = cross_val_score(make_pipeline(StandardScaler(), Ridge(alpha=1.0)), X, y, cv=cv, scoring="r2")
poly = cross_val_score(make_pipeline(PolynomialFeatures(2), StandardScaler(), Ridge(alpha=1.0)), X, y, cv=cv,
                       scoring="r2")
results = {"ridge_r2_mean": float(np.mean(base)), "poly_ridge_r2_mean": float(np.mean(poly)),
           "r2_difference": float(np.mean(poly) - np.mean(base))}
with open("results.json", "w") as f:
    json.dump(results, f, indent=1)
print(results)
