import pandas as pd
import numpy as np
def summarize_rounds(session_df, rounds):
    """Input: Session dataframe; rounds to analyze | Add file name path with .csv
       Output: Column summaries for each round"""
    tot_df = []
    for round in rounds:
        round_df = session_df[session_df['round'] == round]
        numeric_cols = round_df.select_dtypes(include=[np.number])
        mean_df = numeric_cols.mean()
        tot_df.append(mean_df)

    # Convert the list of means to a DataFrame for better visualization
    result_df = pd.DataFrame(tot_df, index=rounds)
    return result_df

def summarize_df(csv_file, file_name = None):
    """Input: CSV File path
       Output: Round by Round data sumamrized across subjects. Mean taken for all numerical column
       Note: THIS HAS NO QUALITATIVE DATA IN IT"""
    raw_data = pd.read_csv(csv_file)
    sessions = np.unique(raw_data['session'])
    session_list = {}
    round_summary = []
    for session in sessions:
        session_list[session] = raw_data[raw_data['session'] == session]
        session_df = session_list[session]
        rounds = np.unique(session_df['round'])
        session_summary = summarize_rounds(session_df, rounds)
        
        # Add a column to identify the session in the summary DataFrame
        session_summary['session'] = session
        round_summary.append(session_summary)

    # Concatenate all the round summaries into a single DataFrame
    final_df = pd.concat(round_summary)

    if file_name != None:
        # Display the final DataFrame
        final_df.to_csv(f"{file_name}") # Will send to whatever dir your code is in

    return final_df

csv_file = r'*[YOU NEED TO INPUT YOUR PATH HERE]*/GitHub/neurobubbles/econometrics/flattened_data_w_bio_7_26_24.csv' # Insert CSV path here, this is my path but you may need to change it

df = summarize_df(csv_file)
