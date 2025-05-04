

import pickle
from sklearn.ensemble import RandomForestClassifier

# Create dummy dataset
X = [[0, 0], [1, 1]]
y = [0, 1]

# Train simple model
model = RandomForestClassifier()
model.fit(X, y)

# Save model
with open("real_sklearn_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ real_sklearn_model.pkl created!")
