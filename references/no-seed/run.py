"""MLP hidden size on digits; no random seed anywhere (the split and the weights change every run)."""
import json

from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

X, y = load_digits(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25)
sc = StandardScaler().fit(X_tr)
X_tr, X_te = sc.transform(X_tr), sc.transform(X_te)
acc = {}
for h in (32, 128):
    m = MLPClassifier(hidden_layer_sizes=(h,), max_iter=300).fit(X_tr, y_tr)
    acc[h] = float(m.score(X_te, y_te))
results = {"mlp32_test_accuracy": acc[32], "mlp128_test_accuracy": acc[128], "accuracy_difference": acc[128] - acc[32]}
with open("results.json", "w") as f:
    json.dump(results, f, indent=1)
print(results)
