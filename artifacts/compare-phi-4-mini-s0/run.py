import json
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

# Load dataset
data = load_breast_cancer()
X = data.data
y = data.target

# Initialize models
rf = RandomForestClassifier()
lr = LogisticRegression()

# Evaluate models with 5-fold cross-validation
rf_scores = cross_val_score(rf, X, y, cv=5, scoring='accuracy')
lr_scores = cross_val_score(lr, X, y, cv=5, scoring='accuracy')

# Calculate mean accuracy
rf_accuracy_mean = np.mean(rf_scores)
lr_accuracy_mean = np.mean(lr_scores)
accuracy_difference = rf_accuracy_mean - lr_accuracy_mean

# Prepare results dictionary
results = {
    'rf_accuracy_mean': rf_accuracy_mean,
    'lr_accuracy_mean': lr_accuracy_mean,
    'accuracy_difference': accuracy_difference
}

# Write results to JSON file
with open('results.json', 'w') as f:
    json.dump(results, f)