import numpy as np
import pandas as pd
from sklearn.datasets import load_wine
from sklearn.utils import resample
import json

# Load the wine dataset
X, y = load_wine(return_X_y=True)

# Separate the data by class
class_0 = X[y == 0]
class_1 = X[y == 1]

# Calculate the mean alcohol content for each class
mean_class_0 = np.mean(class_0[:, 0])
mean_class_1 = np.mean(class_1[:, 0])

# Calculate the difference in means
mean_difference = mean_class_0 - mean_class_1

# Bootstrap resampling
n_iterations = 2000
bootstrap_diffs = []
for _ in range(n_iterations):
    sample_class_0 = resample(class_0, n_samples=len(class_0), replace=True)
    sample_class_1 = resample(class_1, n_samples=len(class_1), replace=True)
    bootstrap_diff = np.mean(sample_class_0[:, 0]) - np.mean(sample_class_1[:, 0])
    bootstrap_diffs.append(bootstrap_diff)

# Calculate the 95% confidence interval
ci_low = np.percentile(bootstrap_diffs, 2.5)
ci_high = np.percentile(bootstrap_diffs, 97.5)

# Write the results to a JSON file
results = {"mean_difference": mean_difference, "ci_low": ci_low, "ci_high": ci_high}
with open("results.json", "w") as f:
    f.write(json.dumps(results))