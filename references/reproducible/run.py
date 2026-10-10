"""Random forest vs logistic regression on breast cancer, 5-fold stratified CV with fixed seeds."""
import json

from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 0
X, y = load_breast_cancer(return_X_y=True)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
rf = cross_val_score(RandomForestClassifier(n_estimators=300, random_state=SEED), X, y, cv=cv)
lr = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000)), X, y, cv=cv)
results = {"rf_accuracy_mean": float(rf.mean()), "lr_accuracy_mean": float(lr.mean()),
           "accuracy_difference": float(rf.mean() - lr.mean())}
with open("results.json", "w") as f:
    json.dump(results, f, indent=1)
print(results)
