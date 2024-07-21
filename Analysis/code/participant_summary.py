import pandas as pd

INPUT_DIR = "Analysis/input"
OUTPUT_DIR = "Analysis/temp"

df = pd.read_csv(f'{INPUT_DIR}/participant.csv')

# date
df['date'] = pd.to_datetime(df['time_started_utc']).dt.date

# site
site_result = df.groupby(['site', 'date']).size().reset_index(name='session_count')
site = site_result.pivot_table(index='date', columns='site', values='session_count', fill_value=0).reset_index()

# age
age = df.groupby('date')['age'].mean().reset_index(name='Mean Age')

# gender
gender_raw = df.groupby(['date', 'gender']).size().reset_index(name='gender_count')
gender_pivot = gender_raw.pivot_table(index='date', columns='gender', values='gender_count', fill_value=0)
gender_pivot['Other'] = gender_raw.get('Non-binary', 0) + gender_pivot.get('I prefer not to say', 0)
gender = gender_pivot[['Female', 'Male', 'Other']].reset_index()

# hispanic
df['hisp'] = df['hisp'].map({'No': 0, 'Yes': 1})
hispanic = df.groupby('date')['hisp'].sum().reset_index(name='Hispanic')

# race
race_raw = df.groupby(['date', 'race']).size().reset_index(name='race_count')
race_pivot = race_raw.pivot_table(index='date', columns='race', values='race_count', fill_value=0)
race_pivot['Unlisted'] = race_pivot.get('What race do you consider yourself? Write here:', 0)
race = race_pivot[['American Indian or Alaska Native', 'Asian or Asian Indian', 'Black or African American', 'White caucasian', 'Unlisted']].reset_index()

# payment
paymentraw = df.groupby(['site', 'date'])['total_payment'].agg(['mean', 'std']).reset_index()
payment_pivot = payment.pivot_table(index='date', columns='site', values=['mean', 'std'], fill_value=0)
payment_pivot.columns = [f'{stat.capitalize()} Payment {site}' for stat, site in payment_pivot.columns]
payment = payment_pivot.reset_index()

# merge
merged = (site
    .merge(age)
    .merge(hispanic)
    .merge(race)
    .merge(payment_pivot)
    .sort_values(by='date'))

# display
# print(merged)
merged.to_csv(f'{OUTPUT_DIR}/participant_summary.csv', index=False)