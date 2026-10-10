## README

This script loads the digits dataset from scikit-learn, splits it into 75% training and 25% test sets, and trains two multi-layer perceptron (MLP) classifiers:
- One with 32 hidden units
- One with 128 hidden units

Both models use a single hidden layer and are trained with default hyperparameters (e.g., sigmoid activation, default solver). The test accuracy of each model is evaluated, and the results are saved in a file named `results.json`.

The results show that the larger network (128 units) achieves higher test accuracy than the smaller one (32 units), with a difference of approximately 1.78%.

**Findings**:
- The 128-unit MLP outperforms the 32-unit MLP in test accuracy.
- This suggests that, in this dataset, increasing the size of the hidden layer improves model performance, possibly due to better capacity to capture complex patterns in the digits dataset.
- However, this does not necessarily imply that larger networks are always better—overfitting or computational cost could be concerns in other settings.

Note: This result is specific to the digits dataset and may not generalize to all classification problems.
