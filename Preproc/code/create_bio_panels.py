import pandas as pd
import os
import sys
import glob
from scipy.stats import skew, kurtosis, zscore
from scipy.signal import find_peaks
import numpy as np
from multiprocessing import Process, Manager#, cpu_count
import datetime

if 'Preproc/code' not in sys.path:
    sys.path.insert(0, 'Preproc/code')

from bio_preproc_funcs import decompose_eda_signal


BIO_TEMP_DIR = 'Preproc/temp/bio'
BIO_PAGE_TEMP_DIR = 'Preproc/temp/bio/page_merge'
BIO_TEMP_PANELS_DIR = 'Preproc/temp/bio/panels'
TEMP_DIR = 'Preproc/temp'
BIO_SOURCE_DIR = 'Data/EDA_data'

#DATA_FILE_NAMES = ['ACC', 'BVP', 'EDA', 'HR', 'IBI', 'TEMP']
DATA_FILE_NAMES = ['EDA', 'HR', 'TEMP']



sess_data = pd.read_csv(f"{TEMP_DIR}/preproc_session.csv").set_index('sess_date')
part_data = pd.read_csv(f"{TEMP_DIR}/preproc_participant.csv")
pt_data = pd.read_csv(f"{TEMP_DIR}/preproc_page_time.csv")


dirs = list(glob.glob(f"{BIO_PAGE_TEMP_DIR}/*"))

# get load the bio marker given a directory and file name
# The participant id is the directoy name.
# Add the part id to the dataframe so we can group by that later
def get_bio_df_for_part(d, fn):
    part_label = os.path.basename(d)
    try:
        df = pd.read_csv(f"{d}/{fn}.csv").dropna()
        df['part_label'] = part_label
        
        # consolidate Risk pages
        df.loc[df.page.str.contains('Risk'), 'page'] = 'RiskPage'
        
        pages_to_keep = ['MarketGridChoice', 'ForecastPage', 'RoundResultsPage', 'RiskPage', ]
        df = df[df.page.isin(pages_to_keep)]
        
        if(df.shape[0] == 0):
            print(f"empty df: {d} - {fn}")
            df = None
            
    except FileNotFoundError:
        df = None
        
    return df


####
# Consolidate bio marker files
def get_bio_df(_dirs, file_name):
    dfs = [get_bio_df_for_part(d, file_name) for d in dirs]
    dfs = [df for df in dfs if df is not None] # remove null entries
    df = pd.concat(dfs).reset_index(drop=True)
    return df

## Generate the statistics for participant-round-page-analysis_type groups
## index name for the resulting Series object are prefixed with the given
## 'col_prefix variable.
def get_stats(ser, idx):
    peaks, _ = find_peaks(ser)
    peak_values = ser[peaks]
 
    stats = {
        'part_label': idx[0],
        'page': idx[1],
        'round': idx[2],
        'mean': np.mean(ser),
        'median': np.median(ser),
        'std': np.std(ser),
        'range': np.ptp(ser),
        'iqr': np.subtract(*np.percentile(ser, [75, 25])),
        'peak_cnt': len(peaks),
        'auc': np.sum(ser),
        'skewness': skew(ser),
        'kurtosis': kurtosis(ser),
        'variance': np.var(ser),
        'peaks_avg': np.mean(peak_values) if peaks.size > 0 else 0
        }
    
    stats = pd.Series(stats)
    return stats


##
# Generate the statistics for participant-round-page group
# Splits the data into tonic and phasic and generates a separate set of stats for each
def process_pg(ser, idx):
    
    if ser.shape[0] <= 18:
        return 
    
    try:
        tonic, phasic = decompose_eda_signal(ser, 4)
        
        tonic_stats = get_stats(tonic, idx)
        phasic_stats = get_stats(phasic, idx)
        return (tonic_stats, phasic_stats)

    except ValueError:
        print(f"Error: {ser.name}")
        raise


def combine_and_extend(sers, col_prefix):
    df = pd.concat(sers, axis='columns').T
    idx_cols = ['part_label', 'page', 'round']
    df.sort_values(idx_cols, inplace=True)
    
    grp_cols = ['part_label', 'page']
    calc_cols = ['mean', 'median', 'std', 'range', 'iqr', 'peak_cnt', 'auc', 'skewness', 'kurtosis', 'variance', 'peaks_avg',]
    
    
    # #print("\t 3P Moving Average")
    # ma_3 = df.groupby(grp_cols)[calc_cols].rolling(3).mean().reset_index(level=2, drop=True)
    # ma_3.rename(mapper=lambda x: 'ma3_' + x, axis='columns', inplace=True)
    # ma_3.reset_index(inplace=True, drop=True)
    
    # #print("\t 5P Moving Average")
    # ma_5 = df.groupby(grp_cols)[calc_cols].rolling(5).mean().reset_index(level=2, drop=True)
    # ma_5.rename(mapper=lambda x: 'ma5_' + x, axis='columns', inplace=True)
    # ma_5.reset_index(inplace=True, drop=True)
    
    # #print("\t Inter-Period Difference")
    # diff_lam = lambda x: x.iloc[1] - x.iloc[0]
    # diff_df = df.groupby(grp_cols)[calc_cols].rolling(2).apply(diff_lam).reset_index(level=2, drop=True)
    # diff_df.rename(mapper=lambda x: 'diff_' + x, axis='columns', inplace=True)
    # diff_df.reset_index(inplace=True, drop=True)
   
    # #print("\t Inter-Period Percentage Change")
    # pct_change = lambda x: (x.iloc[1] - x.iloc[0]) / x.iloc[0]
    # pct_df = df.groupby(grp_cols)[calc_cols].rolling(2).apply(pct_change).reset_index(level=2, drop=True)
    # pct_df.rename(mapper=lambda x: 'pct_' + x, axis='columns', inplace=True)
    # pct_df.reset_index(inplace=True, drop=True)
   
    # Assemble all metrics into one data frame
    # final_df = pd.concat([df, ma_3, ma_5, diff_df, pct_df], axis='columns')
    final_df = df
    final_df.set_index(idx_cols, inplace=True)
    final_df.rename(mapper=lambda x: f'{col_prefix}_{x}', axis='columns', inplace=True)
    
    return final_df    


# Create the panel for the given bio_marker (HR, BVP, EDA, TEMP)
def get_panel(bio_marker):
    
    #print(f"# Processing {bio_marker}")
    bio_eda = get_bio_df(dirs, bio_marker)
    
    #print("\tGenerate Raw Stats")
    groups = bio_eda.groupby(['part_label', 'page', 'rnd'])[['tonic', 'phasic']]
    ton_stats_ser = []
    pha_stats_ser = []
    for idx, page in groups:
        ton_stats_ser.append(get_stats(page.tonic.values, idx))
        pha_stats_ser.append(get_stats(page.phasic.values, idx))

    ton_df = combine_and_extend(ton_stats_ser, 'ton')
    pha_df = combine_and_extend(pha_stats_ser, 'pha')
    
    all_stats = pd.concat([ton_df, pha_df], axis='columns', join='inner')
    return all_stats




##
## Write results to excel spreadsheet
def write_sheet(df, idx, w):
    panel = df.reset_index(level=['part_label', 'round'])
    sheet_name = f'{idx[1]}_{idx[0]}'
    panel.to_excel(w, sheet_name=sheet_name, index=False)

def to_disk(df, fn):
    df.to_csv(f'{BIO_TEMP_PANELS_DIR}/bio_panel_{fn}.csv')
    
    excel_path = f'{BIO_TEMP_PANELS_DIR}/x_bio_panel_{fn}.xlsx'

    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        grps = df.groupby(level='page')
        for idx, df in grps:
            write_sheet(df, idx, writer)



# Mulitprocessing stuff
def task(_iq):
    for args in iter(_iq.get, 'STOP'):
        fn = args[0]
        
        if os.path.exists(f"{BIO_TEMP_PANELS_DIR}/bio_panel_{fn}.csv"):
            print(f"Panel exists: {fn} Skipping...")
            continue
        
        panel = get_panel(fn)
        to_disk(panel, fn)    


if __name__ == '__main__':
    print("###\n###\n### Generate Biometric Panel Data")
    
    start = datetime.datetime.now()

    m = Manager()
    iq = m.Queue()
    num_tasks = 0
    retrieved = 0
    
    num_procs = len(DATA_FILE_NAMES)
    
    procs = [Process(target=task, args=[iq]) for _ in range(num_procs)]
    for p in procs: p.start()
    for dir in DATA_FILE_NAMES:
        iq.put([dir])
        num_tasks += 1
    for _ in range(num_procs):iq.put('STOP')
    for p in procs: p.join()
    
    end = datetime.datetime.now()
    
    print(f"Elapsed Time: {str(end-start)}")


# for fn in DATA_FILE_NAMES:
# for fn in ['HR']:
#     panel = get_panel(fn)
#     print("\t Writing to Disk")
#     to_disk(panel, fn)
