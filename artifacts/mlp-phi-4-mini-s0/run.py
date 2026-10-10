import json
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

# Load dataset
digits = load_digits()
data = digits.data
target = digits.target

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(data, target, test_size=0.25, random_state=42)

# Train and test MLP with 32 hidden units
mlp32 = MLPClassifier(hidden_layer_sizes=(32,), random_state=42)
mlp32.fit(X_train, y_train)
mlp32_test_accuracy = mlp32.score(X_test, y_test)

# Train and test MLP with 128 hidden units
mlp128 = MLPClassifier(hidden_layer_sizes=(128,), random_state=42)
mlp128.fit(X_train, y_train)
mlp128_test_accuracy = mlp128.score(X_test, y_test)

# Calculate accuracy difference
accuracy_difference = mlp128_test_accuracy - mlp32_test_accuracy

# Prepare results dictionary
results = {
    "mlp32_test_accuracy": mlp32_test_accuracy,
    "mlp128_test_accuracy": mlp128_test_accuracy,
    "accuracy_difference": accuracy_difference
}

# Write results to JSON file
with open("results.json", "w") as outfile:
    json.dump(results, outfile)