from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report
from sklearn.svm import SVC
#from sklearn.tree import DecisionReplyClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from xgboost import XGBClassifier
import pandas as pd

# Import data
file_path = '/Users/mihai/PycharmProjects/stockPredict/neurofinance/results/merged_data_4markets.xlsx'
df = pd.read_excel(file_path)

# Create a binary outcome variable for log_returns
df['return_direction'] = (df['log_returns'] > 0).astype(int)

# Define the features to be used
features = [
    'forecast_f0', 'deviation_f0', 'dose_r_ma3',
    'Delta_EDA_ma3.x', 'group.volume'
]
#, 'Delta_percent_EDA_ma3.x, , 'dose_mu_ma3'

# Subset the DataFrame to include only the necessary features
df = df[features + ['return_direction']]

# Split the data into features and target variable
X = df.drop('return_direction', axis=1)
y = df['return_direction']

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Impute missing values and scale features
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

X_train_transformed = pipeline.fit_transform(X_train)
X_test_transformed = pipeline.transform(X_test)

# Logistic Regression with Hyperparameter Tuning
lr_params = {
    'C': [0.1, 1, 10],
    'class_weight': [None, 'balanced']
}
lr_grid = GridSearchCV(LogisticRegression(), param_grid=lr_params, cv=5, scoring='accuracy')
lr_grid.fit(X_train_transformed, y_train)
print("Best parameters for Logistic Regression:", lr_grid.best_params_)
print("Classification Report for Logistic Regression:")
print(classification_report(y_test, lr_grid.predict(X_test_transformed)))

# Naive Bayes Classifier
nb_classifier = GaussianNB()
nb_classifier.fit(X_train_transformed, y_train)
print("Classification Report for Naive Bayes:")
print(classification_report(y_test, nb_classifier.predict(X_test_transformed)))

# XGBoost Classifier
xgb_classifier = XGBClassifier(use_label_encoder=False, eval_metric='logloss')
xgb_classifier.fit(X_train, y_train)
print("Classification Report for XGBoost:")
print(classification_report(y_test, xgb_classifier.predict(X_test)))

# RandomForest with Imputation
rf_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('rf', RandomForestClassifier(random_state=42))
])
rf_params = {
    'rf__n_estimators': [100, 200],
    'rf__max_depth': [None, 10, 20]
}
rf_grid = GridSearchCV(rf_pipeline, param_grid=rf_params, cv=5, scoring='accuracy')
rf_grid.fit(X_train, y_train)
print("Best parameters for Random Forest:", rf_grid.best_params_)
print("Classification Report for Random Forest:")
print(classification_report(y_test, rf_grid.predict(X_test)))

# HistGradientBoosting Classifier
hgbc = HistGradientBoostingClassifier()
hgbc.fit(X_train, y_train)
print("Classification Report for HistGradientBoosting:")
print(classification_report(y_test, hgbc.predict(X_test)))

# ExtraTrees Classifier
etc_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('etc', ExtraTreesClassifier(random_state=42))
])
etc_params = {
    'etc__n_estimators': [100, 200],
    'etc__max_depth': [None, 10, 20]
}
etc_grid = GridSearchCV(etc_pipeline, param_grid=etc_params, cv=5, scoring='accuracy')
etc_grid.fit(X_train, y_train)
print("Best parameters for Extra Trees:", etc_grid.best_params_)
print("Classification Report for Extra Trees:")
print(classification_report(y_test, etc_grid.predict(X_test)))
