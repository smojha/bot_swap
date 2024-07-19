from file_processing import get_file_paths
from file_processing import aggregate_data
from file_processing import get_prices_path
from data_analysis import process_files
import os


def get_all_experiment_codes(base_path):
    # This function scans the base directory and retrieves all possible experiment codes.
    try:
        return [folder for folder in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, folder))]
    except FileNotFoundError:
        return []


def main():
    # The base path and results directory could also be configured here or in a config file
    base_path = '/Users/mihai/PycharmProjects/stockPredict/neurofinance/data/'
    results_path = '/Users/mihai/PycharmProjects/stockPredict/neurofinance/results'
    price_root_location = '/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/'


    # Retrieve all experiment codes from the base path for consistent market_id mapping
    all_experiment_codes = get_all_experiment_codes(base_path)
    market_id_mapping = {code: i + 1 for i, code in enumerate(sorted(all_experiment_codes))}

    # First part: Processing individual experiment files
    experiment_code = input("Enter the experiment code for individual processing: ")
    if experiment_code:  # Ensure there's input before proceeding
        data_type = input("Enter the analysis type for individual processing (EDA, HR, BVP, TEMP): ")

        # Retrieve file paths for the specified experiment
        file_names = get_file_paths(base_path, experiment_code, data_type)
        prices_path = get_prices_path(price_root_location, experiment_code)
        market_id = market_id_mapping.get(experiment_code, None)  # Get market_id from the mapping

        if market_id is None:
            print(f"Error: Experiment code {experiment_code} is not recognized.")
            return

        if prices_path and file_names:
            process_files(file_names, prices_path, data_type, experiment_code, results_path, market_id)
        else:
            if not prices_path:
                print(f"No price data file found for experiment code {experiment_code}.")
            if not file_names:
                print("No files found or invalid directory for individual processing.")

    # Second part: Aggregating data across multiple experiments
    print("Now enter the experiment codes one by one for aggregation. Type 'done' when finished:")
    experiment_codes = []
    while True:
        code = input("Enter experiment code or 'done' to finish: ")
        if code.lower() == 'done':
            break
        if code in market_id_mapping:
            experiment_codes.append(code)
        else:
            print(f"Experiment code {code} is not recognized.")

    if experiment_codes:
        data_type = input("Enter the analysis type for aggregation (EDA, HR, BVP, TEMP): ")
        output_filename = input("Enter the name for the aggregated output file (e.g., EDA_panel.xlsx): ")
        output_path = os.path.join(results_path, output_filename)

        for code in experiment_codes:
            file_names = get_file_paths(base_path, code, data_type)
            prices_path = get_prices_path(price_root_location, code)
            market_id = market_id_mapping[code]

            if prices_path and file_names:
                process_files(file_names, prices_path, data_type, code, results_path, market_id)
            else:
                if not prices_path:
                    print(f"No price data file found for experiment code {code}.")
                if not file_names:
                    print("No files found or invalid directory for individual processing.")

            aggregate_data(results_path, experiment_codes, data_type, output_path)

    else:
        print("No experiment codes entered for aggregation.")


if __name__ == "__main__":
    main()