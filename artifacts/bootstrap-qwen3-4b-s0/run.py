import json
import numpy as np
import pandas as pd
from sklearn.datasets import load_wine

# Load the wine dataset
wine = load_wine()
X, y = wine.data, wine.target

# Extract alcohol content (feature index 3)
alcohol = X[:, 3]

# Separate data by class
alcohol_class0 = alcohol[y == 0]
alcohol_class1 = alcohol[y == 1]

# Compute the observed difference in mean alcohol content
mean_diff = np.mean(alcohol_class0) - np.mean(alcohol_class1)

# Perform bootstrap resampling to compute 95% confidence interval
n_bootstrap = 2000
bootstrapped_diffs = []

for _ in range(n_bootstrap):
    # Resample with replacement for both classes
    idx0 = np.random.choice(len(alcohol_class0), size=len(alcohol_class0), replace=True)
    idx1 = np.random.choice(len(alcohol_class1), size=len(alcohol_class1), replace=True)
    
    # Resample alcohol values
    boot_alc0 = alcohol_class0[idx0]
    boot_alc1 = alcohol_class1[idx1]
    
    # Compute difference in means
    boot_diff = np.mean(boot_alc0) - np.mean(boot_alc1)
    bootstrapped_diffs.append(boot_diff)

# Compute 95% confidence interval (percentile method)
bootstrapped_diffs = np.array(bootstrapped_diffs)
lower = np.percentile(bootstrapped_diffs, 2.5)
upper = np.percentile(bootstrapped_diffs, 97.5)

# Save results to JSON
results = {
    "mean_difference": mean_diff,
    "ci_low": lower,
    "ci_high": upper
}

# Write results to file
with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"Results saved to results.json")