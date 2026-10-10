import json
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

# Load the breast cancer dataset
data = load_breast_cancer()
X, y = data.data, data.target

# Define models
rf_model = RandomForestClassifier(random_state=42)
lr_model = LogisticRegression(random_state=42)

# Perform 5-fold cross-validation on both models
rf_scores = cross_val_score(rf_model, X, y, cv=5, scoring='accuracy')
lr_scores = cross_val_score(lr_model, X, y, cv=5, scoring='accuracy')

# Compute mean accuracies
rf_accuracy_mean = np.mean(rf_scores)
lr_accuracy_mean = np.mean(lr_scores)
accuracy_difference = rf_accuracy_mean - lr_accuracy_mean

# Save results to results.json
results = {
    "rf_accuracy_mean": float(rf_accuracy_mean),
    "lr_accuracy_mean": float(lr_accuracy_mean),
    "accuracy_difference": float(accuracy_difference)
}

with open('results.json', 'w') as f:
    json.dump(results, f, indent=4)