import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


# Function to evaluate classification model performance
def evaluate_classification_model(model, X_test, y_test):
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]  # Probabilities for class 1 (crash)

    # Calculate classification metrics
    accuracy = accuracy_score(y_test, predictions)
    auc_roc = roc_auc_score(y_test, probabilities)
    precision = precision_score(y_test, predictions)
    recall = recall_score(y_test, predictions)
    f1 = f1_score(y_test, predictions)

    return predictions, probabilities, accuracy, auc_roc, precision, recall, f1


# Function to mark crashes: 1s after market peaks and 0s before
def mark_crash(df):
    df['crash'] = 0
    for market_id in df['market_id'].unique():
        market_data = df[df['market_id'] == market_id]
        peak_round = market_data['average_price'].idxmax()  # Find market peak
        df.loc[(df['market_id'] == market_id) & (df.index > peak_round), 'crash'] = 1
    return df


# Import data
file_path = '/Users/mihai/Desktop/Caltech/Neurofinance/data/data_19markets_panel_570obs.xlsx'
df = pd.read_excel(file_path, sheet_name='pdata_ma3_pca')

# Prepare the features and target (crash prediction)
features = ['ma_pc1', 'ma_pc2', 'ma_dose_r', 'ma_dose_mu', 'average_volume', 'average_pl_f0', 'average_pl_f1',
            'average_pl_f2', 'average_pl_f3']

# Mark crash periods
df = mark_crash(df)

# Preprocess the data
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

# Split data into training (80%) and testing (20%) sets based on markets
train_markets, test_markets = train_test_split(df['market_id'].unique(), test_size=0.2, random_state=42, shuffle=True)

# Split the original DataFrame into train and test sets based on market IDs
train_data = df[df['market_id'].isin(train_markets)]
test_data = df[df['market_id'].isin(test_markets)]

# Separate features and target variables for training and testing
X_train = train_data[features]
y_train = train_data['crash']
X_test = test_data[features]
y_test = test_data['crash']

# Apply the pipeline (imputation + scaling) to both training and test data
X_train_transformed = pipeline.fit_transform(X_train)
X_test_transformed = pipeline.transform(X_test)

# Initialize models (including MLPClassifier and SVC)
models = {
    'Logistic Regression': LogisticRegression(),
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'XGBoost': XGBClassifier(),
    'Gradient Boosting': GradientBoostingClassifier(),
    'SVC': GridSearchCV(SVC(probability=True), param_grid={'C': [0.1, 1, 10], 'kernel': ['linear', 'rbf']}, cv=5),
    'MLP': MLPClassifier(hidden_layer_sizes=(50, 30), max_iter=500, random_state=42)
}

# Train models and store performance metrics
model_performance = {}
all_probabilities = {}

for model_name, model in models.items():
    # Train the model
    model.fit(X_train_transformed, y_train)

    # Evaluate model
    predictions, probabilities, accuracy, auc_roc, precision, recall, f1 = evaluate_classification_model(model,
                                                                                                         X_test_transformed,
                                                                                                         y_test)

    # Store results
    model_performance[model_name] = {
        'Accuracy': accuracy,
        'AUC-ROC': auc_roc,
        'Precision': precision,
        'Recall': recall,
        'F1-Score': f1
    }
    all_probabilities[model_name] = probabilities

# Print out model performance
results_df = pd.DataFrame(model_performance).T
print("\nTable of Model Classification Performance Metrics:")
print(results_df)
results_df.to_excel('classification_model_performance_metrics.xlsx', index=True)


# Bar plot for model accuracies
def plot_model_accuracies(results_df):
    fig, ax = plt.subplots(figsize=(10, 6))

    # Extract accuracy values for each model
    accuracies = results_df['Accuracy']

    # Create a bar plot
    ax.barh(accuracies.index, accuracies.values, color='skyblue')
    ax.set_xlabel("Accuracy")
    ax.set_title("Model Accuracies Comparison")

    plt.tight_layout()
    plt.show()


# Plot model accuracies
plot_model_accuracies(results_df)

