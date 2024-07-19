import os
import pandas as pd
import numpy as np

def get_file_paths(base_path, experiment_code, data_type):
    valid_types = ['EDA', 'HR', 'BVP', 'TEMP']
    if data_type not in valid_types:
        print(f"Invalid analysis type. Please choose from {valid_types}.")
        return []

    file_name = f'{data_type}.xlsx'
    experiment_path = os.path.join(base_path, experiment_code, 'empatica')

    if not os.path.exists(experiment_path):
        print(f"The path {experiment_path} does not exist.")
        return []

    # Get all directories within the experiment path, and sort them alphabetically
    subject_folders = sorted([d for d in os.listdir(experiment_path) if os.path.isdir(os.path.join(experiment_path, d))])

    # Generate file paths for each folder
    file_paths = {os.path.join(experiment_path, folder, file_name): folder for folder in subject_folders}

    return file_paths

def get_prices_path(price_root_location, experiment_code):
    prices_path = os.path.join(price_root_location, experiment_code, 'rounds')

    if os.path.exists(prices_path):
        # List all Excel files in the directory
        price_files = [f for f in os.listdir(prices_path) if f.endswith('.xlsx')]

        if price_files:
            # Return the full path to the first found Excel file
            return os.path.join(prices_path, price_files[0])
    return None  # Return None if no file is found or path doesn't exist

def aggregate_data(results_path, experiment_codes, data_type, output_filename):
    all_sheets = {}

    for code in experiment_codes:
        # Construct the filename using the data type and experiment code
        experiment_results_filename = f"{data_type}_{code}_data.xlsx"
        experiment_results_path = os.path.join(results_path, experiment_results_filename)

        if os.path.exists(experiment_results_path):
            # Load all sheets from the Excel file
            xls = pd.read_excel(experiment_results_path, sheet_name=None)
            for sheet_name, data in xls.items():
                # Check if the sheet name is already in the dictionary
                if sheet_name in all_sheets:
                    all_sheets[sheet_name].append(data)
                else:
                    all_sheets[sheet_name] = [data]
        else:
            print(f"Results file not found for experiment code {code}: {experiment_results_path}")

    # Aggregate data for each sheet and save to a new Excel file
    with pd.ExcelWriter(os.path.join(results_path, output_filename), engine='xlsxwriter') as writer:
        for sheet_name, data_frames in all_sheets.items():
            if data_frames:
                # Concatenate all DataFrames for the current sheet
                combined_df = pd.concat(data_frames, ignore_index=True)
                combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Data for {sheet_name} aggregated and saved.")
            else:
                print(f"No data to aggregate for {sheet_name}.")

    print(f"All data aggregated and saved to {output_filename}")



'''
def aggregate_data(results_path, experiment_codes, data_type, output_filename):
    all_data_frames = []

    for code in experiment_codes:
        # The filename is constructed using the data type, code, and a specific format
        experiment_results_filename = f"{data_type}_{code}_data.xlsx"
        experiment_results_path = os.path.join(results_path, experiment_results_filename)

        if os.path.exists(experiment_results_path):
            df = pd.read_excel(experiment_results_path)
            all_data_frames.append(df)
        else:
            print(f"Results file not found for experiment code {code}: {experiment_results_path}")

    if all_data_frames:
        combined_df = pd.concat(all_data_frames, ignore_index=True)
        combined_df.to_excel(output_filename, index=False)
        print(f"All data aggregated and saved to {output_filename}")
    else:
        print("No data frames were loaded, check your file paths and experiment codes.")
'''