import json
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

# Load the digits dataset
digits = load_digits()
X, y = digits.data, digits.target

# Split the data into 75% training and 25% testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

# Define the two MLP models
mlp32 = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=42, early_stopping=True)
mlp128 = MLPClassifier(hidden_layer_sizes=(128,), max_iter=1000, random_state=42, early_stopping=True)

# Train the models
mlp32.fit(X_train, y_train)
mlp128.fit(X_train, y_train)

# Evaluate on test set
accuracy_32 = mlp32.score(X_test, y_test)
accuracy_128 = mlp128.score(X_test, y_test)

# Compute the difference
accuracy_difference = accuracy_128 - accuracy_32

# Write results to results.json
results = {
    "mlp32_test_accuracy": float(accuracy_32),
    "mlp128_test_accuracy": float(accuracy_128),
    "accuracy_difference": float(accuracy_difference)
}

with open("results.json", "w") as f:
    json.dump(results, f, indent=4)