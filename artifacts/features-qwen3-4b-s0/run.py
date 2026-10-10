import json
import numpy as np
from sklearn.datasets import load_diabetes
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import PolynomialFeatures

# Load the diabetes dataset
data = load_diabetes()
X, y = data.data, data.target

# Define the models to evaluate

# Model 1: Ridge regression on original features
ridge = Ridge()

# Model 2: Ridge regression with degree-2 polynomial features
poly = PolynomialFeatures(degree=2, include_bias=False)
X_poly = poly.fit_transform(X)
ridge_poly = Ridge()

# Perform 5-fold cross-validation on both models using R² scoring

# Cross-validation scores for original ridge
ridge_scores = cross_val_score(ridge, X, y, cv=5, scoring='r2')

# Cross-validation scores for polynomial ridge
poly_scores = cross_val_score(ridge_poly, X_poly, y, cv=5, scoring='r2')

# Compute mean R² scores
ridge_r2_mean = np.mean(ridge_scores)
poly_r2_mean = np.mean(poly_scores)
r2_difference = poly_r2_mean - ridge_r2_mean

# Save results to results.json
results = {
    "ridge_r2_mean": float(ridge_r2_mean),
    "poly_ridge_r2_mean": float(poly_r2_mean),
    "r2_difference": float(r2_difference)
}

with open('results.json', 'w') as f:
    json.dump(results, f, indent=4)