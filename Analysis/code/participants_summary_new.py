import pandas as pd

df = pd.read_csv('/Users/cadyngo/Desktop/participant.csv')

# Ensure 'session' column is treated as a categorical variable
df['session'] = df['session'].astype('category')

# site
site_result = df.groupby(['site', 'session']).size().reset_index(name='session_count')
site = site_result.pivot_table(index='session', columns='site', values='session_count', fill_value=0).reset_index()

# age
age = df.groupby('session')['surv_age'].mean().reset_index(name='Mean Age')

# gender
gender_raw = df.groupby(['session', 'surv_gender']).size().reset_index(name='gender_count')
gender_pivot = gender_raw.pivot_table(index='session', columns='surv_gender', values='gender_count', fill_value=0)
gender_pivot['Other'] = gender_raw.get('Non-binary', 0) + gender_raw.get('I prefer not to say', 0)
gender = gender_pivot[['Female', 'Male', 'Other']].reset_index()

# hispanic
df['hisp'] = df['surv_hisp'].map({'No': 0, 'Yes': 1})
hispanic = df.groupby('session')['hisp'].sum().reset_index(name='Hispanic')

# race
race_raw = df.groupby(['session', 'surv_race']).size().reset_index(name='race_count')
race_pivot = race_raw.pivot_table(index='session', columns='surv_race', values='race_count', fill_value=0)
race_pivot['Unlisted'] = race_pivot.get('What race do you consider yourself? Write here:', 0)
race = race_pivot[['American Indian or Alaska Native', 'Asian or Asian Indian', 'Black or African American', 'White caucasian', 'Unlisted']].reset_index()

# payment
payment = df.groupby(['site', 'session'])['total_payment'].agg(['mean', 'std']).reset_index()
payment_pivot = payment.pivot_table(index='session', columns='site', values=['mean', 'std'], fill_value=0)
payment_pivot.columns = [f'{stat.capitalize()} Payment {site}' for stat, site in payment_pivot.columns]
payment_pivot = payment_pivot.reset_index()

# merge
merged = (site
    .merge(age, on='session', how='outer')
    .merge(hispanic, on='session', how='outer')
    .merge(race, on='session', how='outer')
    .merge(payment_pivot, on='session', how='outer')
    .sort_values(by='session'))

merged.fillna(0, inplace=True)

# display
print(merged)
merged.to_csv('/Users/cadyngo/Desktop/participants_summary.csv', index=False)

# counts
lab_sum = merged['Lab'].sum()
print(f"Sum of Lab: {lab_sum}")
prolific_sum = merged['Prolific'].sum()
print(f"Sum of Prolific: {prolific_sum}")