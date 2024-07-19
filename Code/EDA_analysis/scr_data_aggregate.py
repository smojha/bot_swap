import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import skew, kurtosis, zscore
from scipy.signal import find_peaks, butter, lfilter, filtfilt, detrend
from preprocessing_functions import butter_highpass, butter_highpass_filter, butter_lowpass, butter_lowpass_filter, decompose_eda_signal, normalize_signal
from statsmodels.tsa.stattools import adfuller, acf, pacf
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import os

experiment_code = 'hybrid_0404'

file_names_eda = ['/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0404/empatica/07C/EDA.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0404/empatica/31O/EDA.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0404/empatica/47R/EDA.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0404/empatica/63X/EDA.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0404/empatica/90M/EDA.xlsx']


# Import prices
price_df = pd.read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/04_04_2024_hybrid/rounds_2024-04-04.xlsx', sheet_name='price')
price = price_df['price']
period = price_df['period']


# Define durations for sub-trials and total duration per round if not already defined
durations = [20, 20, 10, 20]  # Durations for each sub-trial
total_duration_per_round = sum(durations)  # Total duration of all sub-trials in a round


def process_files(file_names, data_type, sensor_type, experiment_code):
    # Dictionary to hold all subjects' data for each sub-trial and analysis type
    all_data = {
        'Tonic': {'Order-submission': pd.DataFrame(), 'Price Forecast': pd.DataFrame(),
                  'Round Results': pd.DataFrame(), 'Risk Elicitation': pd.DataFrame()},
        'Phasic': {'Order-submission': pd.DataFrame(), 'Price Forecast': pd.DataFrame(),
                   'Round Results': pd.DataFrame(), 'Risk Elicitation': pd.DataFrame()}
    }

    dfs_to_save = []
    subject_counter = 1  # Start counter for subject naming

    for file_index, file_name in enumerate(file_names):
        df = pd.read_excel(file_name)
        subject_id = f'subject_{subject_counter}'
        subject_counter += 1  # Increment for the next subject

        if isinstance(df['Time'].iloc[0], str):
            df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S.%f')
        df['Time'] = df['Time'] - df['Time'].dt.normalize()

        df = df[(np.abs(zscore(df[data_type])) < 2.5)] # Remove extreme values

        fs = 4  # Sampling frequency, adjust as necessary
        tonic, phasic = decompose_eda_signal(df[data_type].values, fs) # Check if these need to be reversed, i.e tonic, phasic = decompose_eda_signal(df[data_type].values, fs)

        # Drop first 15 minutes. Participants are there only for 30 mins before market starts.

        initial_time = df['Time'].iloc[0]
        # Now, calculate the time difference
        baseline_period = df[df['Time'] < (initial_time + timedelta(minutes=15))][data_type] # This needs to be adjusted based on each experiment

        tonic_normalized = normalize_signal(tonic, baseline_period.values)
        phasic_normalized = normalize_signal(phasic, baseline_period.values)

        # Create a new DataFrame to hold tonic and phasic components
        df_tonic_phasic = pd.DataFrame({
            'Tonic': tonic_normalized,
            'Phasic': phasic_normalized
        })

        # Append the DataFrame to the list
        dfs_to_save.append(df_tonic_phasic)

        # Save each pair of tonic and phasic components to a CSV file
        output_filename = f'output_tonic_phasic_{file_index + 1}.csv'
        df_tonic_phasic.to_csv(output_filename, index=False)
        print(f"Saved: {output_filename}")

        analysis_columns = {'Tonic': tonic_normalized, 'Phasic': phasic_normalized}

        for analysis_type, signal in analysis_columns.items():
            for sub_trial in range(1, 5):
                subject_data = []
                prev_price = None  # Initialize previous price as None
                for round_num in range(1, 31):
                    current_price = price_df.loc[price_df['period'] == round_num, 'price'].values[0]
                    if prev_price is not None:  # Check if there is a previous price to compare with
                        log_price_change = np.log(current_price) - np.log(prev_price)
                    else:
                        log_price_change = None  # For the first observation, leave it as None

                    sub_trial_data = {'id': file_index + 1,
                                      'period': round_num, 'Price': current_price, 'log_price_change': log_price_change,
                                      'Mean': None, 'Median': None, 'Std': None, 'Range': None, 'IQR': None,
                                      'Peak Count': None, 'AUC': None, 'Skewness': None, 'Kurtosis': None,
                                      'Variance': None, 'Peaks Avg': None}
                    # Update prev_price for the next iteration
                    prev_price = current_price

                    round_start_time = df['Time'].iloc[0] + timedelta(
                        seconds=total_duration_per_round * (round_num - 1))
                    sub_trial_start_time = round_start_time + timedelta(seconds=sum(durations[:sub_trial - 1]))
                    sub_trial_end_time = sub_trial_start_time + timedelta(seconds=durations[sub_trial - 1])

                    time_mask = (df['Time'] >= sub_trial_start_time) & (df['Time'] < sub_trial_end_time)
                    sub_trial_signal = signal[time_mask.values[:len(signal)]]

                    if len(sub_trial_signal) > 0:
                        peaks, _ = find_peaks(sub_trial_signal)
                        peak_values = sub_trial_signal[peaks]
                        sub_trial_data.update({
                            'Mean': np.mean(sub_trial_signal),
                            'Median': np.median(sub_trial_signal),
                            'Std': np.std(sub_trial_signal),
                            'Range': np.ptp(sub_trial_signal),
                            'IQR': np.subtract(*np.percentile(sub_trial_signal, [75, 25])),
                            'Peak Count': len(peaks),
                            'AUC': np.sum(sub_trial_signal),
                            'Skewness': skew(sub_trial_signal),
                            'Kurtosis': kurtosis(sub_trial_signal),
                            'Variance': np.var(sub_trial_signal),
                            'Peaks Avg': np.mean(peak_values) if peaks.size > 0 else 0
                        })
                    subject_data.append(sub_trial_data)

                # Reset prev_price for the next subject or sub_trial
                prev_price = None

                # Determine the sub-trial task name based on sub_trial number
                task_name = ['Order-submission', 'Price Forecast', 'Round Results', 'Risk Elicitation'][sub_trial - 1]

                # Append data to the correct DataFrame
                df_subject_data = pd.DataFrame(subject_data)
                all_data[analysis_type][task_name] = pd.concat([all_data[analysis_type][task_name], df_subject_data],
                                                               ignore_index=True)

    # Saving logic
    results_path = '/Users/mihai/PycharmProjects/stockPredict/neurofinance/results'
    save_path = f'{results_path}/{sensor_type}_{experiment_code}_data.xlsx'
    with pd.ExcelWriter(save_path, engine='xlsxwriter') as writer:
        for analysis_type, tasks in all_data.items():
            for task_name, data in tasks.items():
                sheet_name = f'{analysis_type} {task_name}'
                data.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"All subjects' data has been saved to {save_path}")

# Process EDA files
process_files(file_names_eda, 'EDA', 'EDA', experiment_code)