import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, explained_variance_score, max_error
from xgboost import XGBRegressor
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM
from scikeras.wrappers import KerasRegressor
import numpy as np
import matplotlib.pyplot as plt

# Function to create the ANN model
def create_ann():
    model = Sequential()
    model.add(Dense(64, input_dim=X_train.shape[1], activation='relu'))
    model.add(Dense(32, activation='relu'))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
    return model

# Function to create an LSTM model
def create_lstm():
    model = Sequential()
    model.add(LSTM(50, activation='relu', input_shape=(X_train_lstm.shape[1], X_train_lstm.shape[2])))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
    return model

# Function to evaluate model performance
def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)
    mse = mean_squared_error(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, predictions)
    explained_var = explained_variance_score(y_test, predictions)
    max_err = max_error(y_test, predictions)

    return predictions, mse, mae, rmse, r2, explained_var, max_err

# Function to average forecasts across markets
def average_forecasts_by_market(test_data, predictions):
    test_data['predictions'] = predictions
    avg_forecasts = test_data.groupby('round')['predictions'].mean()  # Average across all test markets by round
    return avg_forecasts

# Function to average forecasts and actual returns by market
def average_by_market(test_data, predictions):
    test_data['predictions'] = predictions
    avg_actual_returns = test_data.groupby('round')['average_log_returns'].mean()  # Average actual returns by round
    avg_predictions = test_data.groupby('round')['predictions'].mean()  # Average predictions by round
    return avg_actual_returns, avg_predictions

# Import data
file_path = '/Users/mihai/Desktop/Caltech/Neurofinance/data/data_19markets_panel_570obs.xlsx'
df = pd.read_excel(file_path, sheet_name='pdata_ma3_pca')

# Shift forecast variables by round
df['average_pl_f1'] = df.groupby('market_id')['average_pl_f1'].shift(2)
df['average_pl_f2'] = df.groupby('market_id')['average_pl_f2'].shift(5)
df['average_pl_f3'] = df.groupby('market_id')['average_pl_f3'].shift(10)

# Fill missing forecast values with the first available value
df['average_pl_f1'] = df['average_pl_f1'].fillna(df['average_pl_f1'].dropna().iloc[0])
df['average_pl_f2'] = df['average_pl_f2'].fillna(df['average_pl_f2'].dropna().iloc[0])
df['average_pl_f3'] = df['average_pl_f3'].fillna(df['average_pl_f3'].dropna().iloc[0])

# Calculate deviations between price and forecast values
df['dev_f0'] = df['average_price'] - df['average_pl_f0']
df['dev_f1'] = df['average_price'] - df['average_pl_f1']
df['dev_f2'] = df['average_price'] - df['average_pl_f2']
df['dev_f3'] = df['average_price'] - df['average_pl_f3']

# Define the features to be used
features = ['ma_pc1', 'ma_pc2', 'ma_dose_r', 'ma_dose_mu', 'average_volume',
            'average_pl_f0', 'average_pl_f1', 'average_pl_f2', 'average_pl_f3']

# Ensure no missing values in 'average_log_returns'
df.dropna(subset=['average_log_returns'], inplace=True)

# Get unique market IDs
market_ids = df['market_id'].unique()

# Split data into training (80%) and testing (20%) sets based on markets
train_markets, test_markets = train_test_split(market_ids, test_size=0.2, random_state=42, shuffle=True)

# Split the original DataFrame into train and test sets based on market IDs
train_data = df[df['market_id'].isin(train_markets)]
test_data = df[df['market_id'].isin(test_markets)]

# Separate features and target variables for training and testing
X_train = train_data[features]
y_train = train_data['average_log_returns']
X_test = test_data[features]
y_test = test_data['average_log_returns']

# Preprocess the data
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

X_train_transformed = pipeline.fit_transform(X_train)
X_test_transformed = pipeline.transform(X_test)

# For LSTM, reshape to 3D array (samples, timesteps, features)
X_train_lstm = X_train_transformed.reshape((X_train_transformed.shape[0], 1, X_train_transformed.shape[1]))
X_test_lstm = X_test_transformed.reshape((X_test_transformed.shape[0], 1, X_test_transformed.shape[1]))

# Initialize KFold cross-validation (with 10 splits, only on the training set)
kf = KFold(n_splits=10, shuffle=True, random_state=42)

# Dictionary to store predictions across folds
all_predictions = {
    'XGBoost': [],
    'SVR': [],
    'RandomForest': [],
    'HistGradientBoosting': [],
    'ExtraTrees': [],
    'ANN': [],
    'MLP': [],
    'LSTM': []
}

# Dictionary to store model metrics
model_metrics = {}

# Define models (including MLP and SVR)
models = {
    'XGBoost': XGBRegressor(),
    'SVR': GridSearchCV(SVR(), param_grid={'C': [0.1, 1, 10], 'kernel': ['linear', 'rbf']},
                        cv=5, scoring='neg_mean_squared_error'),
    'RandomForest': RandomForestRegressor(random_state=42),
    'HistGradientBoosting': HistGradientBoostingRegressor(random_state=42),
    'ExtraTrees': ExtraTreesRegressor(random_state=42),
    'ANN': KerasRegressor(build_fn=create_ann, epochs=100, batch_size=10, verbose=0),
    'MLP': MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42),
    'LSTM': KerasRegressor(build_fn=create_lstm, epochs=50, batch_size=10, verbose=0)
}

# KFold cross-validation loop for training on different splits
for train_index, val_index in kf.split(X_train_transformed):
    X_train_fold, X_val_fold = X_train_transformed[train_index], X_train_transformed[val_index]
    y_train_fold, y_val_fold = y_train.iloc[train_index], y_train.iloc[val_index]

    # For LSTM, reshape to 3D for training
    X_train_fold_lstm = X_train_fold.reshape((X_train_fold.shape[0], 1, X_train_fold.shape[1]))
    X_val_fold_lstm = X_val_fold.reshape((X_val_fold.shape[0], 1, X_val_fold.shape[1]))

    # Train models and store predictions
    for model_name, model in models.items():
        if model_name == 'LSTM':  # Special case for LSTM
            model.fit(X_train_fold_lstm, y_train_fold)
            predictions, mse, mae, rmse, r2, explained_var, max_err = evaluate_model(model, X_val_fold_lstm, y_val_fold)
        else:
            model.fit(X_train_fold, y_train_fold)
            predictions, mse, mae, rmse, r2, explained_var, max_err = evaluate_model(model, X_val_fold, y_val_fold)

        model_metrics[model_name] = [mse, mae, rmse, r2, explained_var, max_err]

# After K-Fold, evaluate the final model performance on the test set
final_predictions = {}
avg_actual_returns_by_market = {}

for model_name, model in models.items():
    # Retrain each model on the full training data
    if model_name == 'LSTM':  # Special case for LSTM
        model.fit(X_train_lstm, y_train)
        test_predictions, mse, mae, rmse, r2, explained_var, max_err = evaluate_model(model, X_test_lstm, y_test)
    else:
        model.fit(X_train_transformed, y_train)
        test_predictions, mse, mae, rmse, r2, explained_var, max_err = evaluate_model(model, X_test_transformed, y_test)

    final_predictions[model_name] = test_predictions
    model_metrics[model_name] = [mse, mae, rmse, r2, explained_var, max_err]

    # Get the averaged actual returns and predictions by market
    avg_actual, avg_pred = average_by_market(test_data, test_predictions)
    avg_actual_returns_by_market[model_name] = avg_actual
    final_predictions[model_name] = avg_pred

# Print final model performance metrics
results_df = pd.DataFrame.from_dict(model_metrics, orient='index',
                                    columns=['MSE', 'MAE', 'RMSE', 'R2', 'Explained Variance', 'Max Error'])
print("\nTable of Final Model Performance Metrics:")
print(results_df)
results_df.to_excel('final_model_performance_metrics.xlsx', index=True)


# Function to assign 1s after the market crash and 0s before the crash
def mark_crash(test_data):
    test_data['crash'] = 0
    for market_id in test_data['market_id'].unique():
        market_data = test_data[test_data['market_id'] == market_id]
        peak_round = market_data['average_price'].idxmax()  # Find market peak
        test_data.loc[(test_data['market_id'] == market_id) & (test_data.index > peak_round), 'crash'] = 1
    return test_data


# Mark crash periods
test_data = mark_crash(test_data)
print(test_data[['market_id', 'round', 'crash']].head())


# Function to calculate the average market price across all markets for each round
def average_market_price(df):
    avg_price = df.groupby('round')['average_price'].mean()  # Average price by round
    return avg_price


# Calculate the average market price across all markets for each round
avg_market_price = df.groupby('round')['average_price'].mean()

# Get the maximum number of rounds in the dataset to restrict x-axis
max_round = df['round'].max()


# Function to identify crash periods (from max price to a fixed period after the crash)
def get_crash_periods(df, post_crash_rounds=5):
    crash_periods = []
    for market_id in df['market_id'].unique():
        market_data = df[df['market_id'] == market_id]
        peak_round = market_data['average_price'].idxmax()  # Find market peak
        # Define crash period as the peak to a few rounds (e.g., 5 rounds) after the peak
        last_round = min(peak_round + post_crash_rounds, max_round)  # Ensure it does not exceed max round
        crash_periods.append((peak_round, last_round))  # Crash from peak to few rounds after
    return crash_periods


# Function to plot each model with average market price and crash shading
def plot_model_predictions_with_crash(avg_market_price, crash_periods, avg_actual, avg_pred, model_name):
    # Create figure with two subplots: one for price and one for returns vs predictions
    fig, axs = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [1, 1]})

    # Subplot 1: Average Market Price with Crash Shading
    axs[0].plot(avg_market_price.index, avg_market_price.values, label="Average Market Price", color='blue')
    axs[0].set_title(f"Average Market Price (All Markets) with Crash Shading")
    axs[0].set_ylabel("Price")
    axs[0].set_xlim([0, max_round])  # Limit x-axis to the max number of rounds

    # Add shading for crash periods (correct the span)
    for peak_round, last_round in crash_periods:
        axs[0].axvspan(peak_round, last_round, color='red', alpha=0.3,
                       label="Crash Period" if peak_round == crash_periods[0][0] else None)

    axs[0].legend()

    # Subplot 2: Returns vs Predictions with Crash Shading
    axs[1].plot(avg_actual.index, avg_actual.values, label="Avg Actual Returns", color='blue')
    axs[1].plot(avg_pred.index, avg_pred.values, label=f"Avg {model_name} Predictions", color='green',
                linestyle='dashed')
    axs[1].set_title(f"{model_name} Predictions vs Actual (by Market)")
    axs[1].set_ylabel("Returns")
    axs[1].set_xlim([0, max_round])  # Limit x-axis to the max number of rounds
    axs[1].legend()

    # Add shading for crash periods (correct the span)
    for peak_round, last_round in crash_periods:
        axs[1].axvspan(peak_round, last_round, color='red', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{model_name}_predictions_vs_actual.png')  # Save each plot
    plt.show()


# Get crash periods (define how many rounds after peak to be considered crash)
crash_periods = get_crash_periods(df, post_crash_rounds=5)

# Loop through each model to create a separate figure
for model_name in final_predictions.keys():
    avg_actual = avg_actual_returns_by_market[model_name]
    avg_pred = final_predictions[model_name]

    # Plot predictions and actual returns with crash period for this model
    plot_model_predictions_with_crash(avg_market_price, crash_periods, avg_actual, avg_pred, model_name)