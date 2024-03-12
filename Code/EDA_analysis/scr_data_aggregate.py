import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import skew, kurtosis, zscore
from scipy.signal import find_peaks, butter, lfilter, filtfilt, detrend
from statsmodels.tsa.stattools import adfuller, acf, pacf
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import os

# change here with updated file path
#experiment_code = 'pilot_1130' # find logic to load file_names_eda according to experiment_code
experiment_code = 'hybrid_0307'

'''
file_names_eda = ['/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/pilot_1130/empatica/1701384593_A00893_subject1_1130/EDA_with_time.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/pilot_1130/empatica/1701384575_A017C2_subject2_1130/EDA_with_time.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/pilot_1130/empatica/1701384599_A027E3_subject3_1130/EDA_with_time.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/pilot_1130/empatica/1701384586_A02238_subject4_1130/EDA_with_time.xlsx']
'''

file_names_eda = ['/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0307/empatica/46Y/EDA_with_time.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0307/empatica/24O/EDA_with_time.xlsx',
                  '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/hybrid_0307/empatica/XXX_Alexander_missing3digit_SSEL05/EDA_with_time.xlsx']


# Import times

df = pd.read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/03_07_2024_hybrid/PageTimes-2024-03-07.csv')
df['ts'] = pd.to_datetime(df.epoch_time_completed, unit='s', utc=True).dt.tz_convert('America/New_York')
df[df.session_code=='8h0lckuw']

# Import prices
price_df = pd.read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/03_07_2024_hybrid/rounds_2024-03-07.xlsx', sheet_name='price')
price  =  price_df['price']
period =  price_df['period']

# Define durations for sub-trials and total duration per round if not already defined
durations = [20, 20, 10, 20]  # Example durations for each sub-trial
total_duration_per_round = sum(durations)  # Total duration of all sub-trials in a round


def butter_highpass(cutoff, fs, order=5):
    """
    Designs a high-pass Butterworth filter.

    Parameters:
    - cutoff: the cutoff frequency of the filter.
    - fs: the sampling rate of the signal.
    - order: the order of the filter.

    Returns:
    - b, a: numerator (b) and denominator (a) polynomials of the IIR filter.
    """
    nyq = 0.5 * fs  # Nyquist frequency
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return b, a

def butter_highpass_filter(data, cutoff, fs, order=5):
    """
    Applies a high-pass Butterworth filter to a signal.

    Parameters:
    - data: the input signal.
    - cutoff: the cutoff frequency of the filter.
    - fs: the sampling rate of the signal.
    - order: the order of the filter.

    Returns:
    - y: the filtered signal.
    """
    b, a = butter_highpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y


def decompose_eda_signal(eda_signal, fs):
    # Apply detrend to remove linear trend from the signal
    eda_detrended = detrend(eda_signal)

    # Define cutoff frequencies for high-pass and low-pass filters
    # Adjust these values as needed for your analysis
    highcut_tonic = 0.5  # Low-pass filter cutoff frequency for tonic component
    lowcut_phasic = 0.5  # High-pass filter cutoff frequency for phasic component

    # Extract tonic component using low-pass filter
    tonic = butter_lowpass_filter(eda_detrended, highcut_tonic, fs, order=5)

    # Extract phasic component using high-pass filter
    # Note: The phasic component is typically derived by subtracting the tonic from the original signal
    # or directly filtering the original/detrended signal with a high-pass filter.
    phasic = butter_highpass_filter(eda_detrended, lowcut_phasic, fs, order=5)

    return tonic, phasic


def normalize_signal(signal, baseline_period):
    baseline_value = baseline_period.mean()
    baseline_std = baseline_period.std()
    normalized_signal = (signal - baseline_value) / baseline_std
    return normalized_signal

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

        df = df[(np.abs(zscore(df[data_type])) < 3)] # Remove extreme values

        fs = 4  # Sampling frequency, adjust as necessary
        phasic, tonic = decompose_eda_signal(df[data_type].values, fs) # Check if these need to be reversed, i.e tonic, phasic = decompose_eda_signal(df[data_type].values, fs)

        # Create a new DataFrame to hold tonic and phasic components
        df_tonic_phasic = pd.DataFrame({
            'Tonic': tonic,
            'Phasic': phasic
        })

        # Save each pair of tonic and phasic components to a CSV file
        output_filename = f'output_tonic_phasic_{file_index + 1}.csv'
        df_tonic_phasic.to_csv(output_filename, index=False)
        print(f"Saved: {output_filename}")

        initial_time = df['Time'].iloc[0]
        # Now, calculate the time difference
        baseline_period = df[df['Time'] < (initial_time + timedelta(minutes=15))][data_type] # This needs to be changed and increased

        # Append the DataFrame to the list
        dfs_to_save.append(df_tonic_phasic)

        tonic_normalized = normalize_signal(tonic, baseline_period.values)
        phasic_normalized = normalize_signal(phasic, baseline_period.values)

        analysis_columns = {'Tonic': tonic_normalized, 'Phasic': phasic_normalized}

        for analysis_type, signal in analysis_columns.items():
            for sub_trial in range(1, 5):
                subject_data = []
                for round_num in range(1, 31):
                    current_price = price_df.loc[price_df['period'] == round_num, 'price'].values[0]
                    sub_trial_data = {'Subject ID': 'subject_' + str(file_index + 1),
                                      'period': round_num, 'Price': current_price,
                                      'Mean': None, 'Median': None, 'Std': None, 'Range': None, 'IQR': None,
                                      'Peak Count': None, 'AUC': None, 'Skewness': None, 'Kurtosis': None,
                                      'Variance': None, 'Peaks Avg': None}
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

                # Determine the sub-trial task name based on sub_trial number
                task_name = ['Order-submission', 'Price Forecast', 'Round Results', 'Risk Elicitation'][sub_trial - 1]

                # Append data to the correct DataFrame
                df_subject_data = pd.DataFrame(subject_data)
                all_data[analysis_type][task_name] = pd.concat([all_data[analysis_type][task_name], df_subject_data],
                                                               ignore_index=True)

    # Saving logic
    save_path = f'data_analysis/{sensor_type}_{experiment_code}_data.xlsx'
    with pd.ExcelWriter(save_path, engine='xlsxwriter') as writer:
        for analysis_type, tasks in all_data.items():
            for task_name, data in tasks.items():
                sheet_name = f'{analysis_type} {task_name}'
                data.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"All subjects' data has been saved to {save_path}")

# Process EDA files
process_files(file_names_eda, 'EDA', 'EDA', experiment_code)