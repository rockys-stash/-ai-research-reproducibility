import json
from sklearn.datasets import load_diabetes
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
import numpy as np

# Load the diabetes dataset
X, y = load_diabetes(return_X_y=True)

# Define the base models
ridge = Ridge()
poly_ridge = make_pipeline(PolynomialFeatures(degree=2), Ridge())

# Evaluate the models using 5-fold cross-validation
ridge_r2_scores = cross_val_score(ridge, X, y, scoring='r2', cv=5)
poly_ridge_r2_scores = cross_val_score(poly_ridge, X, y, scoring='r2', cv=5)

# Calculate the mean R² scores
ridge_r2_mean = np.mean(ridge_r2_scores)
poly_ridge_r2_mean = np.mean(poly_ridge_r2_scores)
r2_difference = poly_ridge_r2_mean - ridge_r2_mean

# Prepare the results dictionary
results = {
    "ridge_r2_mean": ridge_r2_mean,
    "poly_ridge_r2_mean": poly_ridge_r2_mean,
    "r2_difference": r2_difference
}

# Write the results to a JSON file
with open('results.json', 'w') as f:
    json.dump(results, f)