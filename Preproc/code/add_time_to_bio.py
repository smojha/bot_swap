import pandas as pd
import glob
import os
from scipy.stats import zscore
from pathlib import Path
import pandas.io.common
from multiprocessing import Process, Manager, cpu_count #, set_start_method
import sys

if 'Preproc/code' not in sys.path:
    sys.path.insert(0, 'Preproc/code')

from bio_preproc_funcs import decompose_eda_signal


BIO_TEMP_DIR = 'Preproc/temp/bio/page_merge'
TEMP_DIR = 'Preproc/temp'
BIO_SOURCE_DIR = 'Data/EDA_data'
DATA_FILE_NAMES = ['ACC', 'BVP', 'EDA', 'HR', 'IBI', 'TEMP']
OUTLIER_THOLD = 2.5

def get_part_label_for_dir(part_dir, part_data):
    # the participant id is the directory name
    id = os.path.basename(part_dir)
    
    #some bio folders refer to non-existent ids, skip them
    if part_data[part_data.plab_short == id].shape[0] == 0:
        print(f"Id in bio data not in experiment data: {id}")
        return
    
    part_label = part_data[part_data.plab_short == id].part_label.values[0]


    # find session
    #parent_dir = os.path.basename(os.path.dirname(part_dir)) # the parent directory name contains the session date
    #date_of_session = "20" + parent_dir[-8:].replace("_", "-") # turn parent directory name into label stored in session data
    #sess = sess_data.loc[date_of_session].session # use the label to get the session code.  
    
    return part_label


def set_up(skip=True):

    # This is to aviod a warning message that comes from huggingface 
    #(dont' know why since I'm not using it here)    
    # https://stackoverflow.com/questions/62691279/how-to-disable-tokenizers-parallelism-true-false-warning
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    
    #sess_data = pd.read_csv(f"{TEMP_DIR}/preproc_session.csv").set_index('label')
    part_data = pd.read_csv(f"{TEMP_DIR}/preproc_participant.csv")
    pt_data = pd.read_csv(f"{TEMP_DIR}/preproc_page_time.csv")

    # check for duplicate participant ids
    part_data = part_data[part_data.site == 'Lab']  # lose the prolific participants
    # shorten the participant labels to 3 characters to match the bio directories
    part_data['plab_short'] = part_data.part_label.str[-3:] 
    # Check for duplicate ids
    c = part_data.groupby('plab_short').session.count()
    dups =  c[c>1]
    # Alert if there are duplicates detected
    if dups.shape[0] > 0:
        print("Found duplicate ids")
        print(dups)
        
    # Reduce the pagee time data to in-lab participants and add a shorteded part_label
    pt_data = pt_data.set_index('part_label').loc[part_data.part_label]
    pt_data = pt_data.join(part_data.set_index('part_label').plab_short)
    pt_data['tse'] = pt_data.tse.apply(pd.Timestamp)
    
    
    dirs = [f for f in glob.glob(f"{BIO_SOURCE_DIR}/Hybrid_*/*") if len(os.path.basename(f)) == 3]
    args = [(d, get_part_label_for_dir(d, part_data)) for d in dirs]
    
    # Skip participants that already exist in the BIO_TEMP_DIR folder
    args_to_keep = []
    for part_dir, part_label in args:
        
        if part_label is None:
            continue
            
        #Test if the directory exists already
        if os.path.exists(f"{BIO_TEMP_DIR}/{part_label}") and skip:
            print(f"Folder exists - {part_label}.   Skipping")
        
        else:
            args_to_keep.append((part_dir, part_label))
    
    
    #Make output dir
    Path(BIO_TEMP_DIR).mkdir(parents=True, exist_ok=True)
    
    return args_to_keep, pt_data


# Add time column.
# Most data are formatted as the column names are the start time as number of seconds since the epoch
# The second row contains the frequency of the data
# the rest of the rows are the measurements.
def add_time(df, colname):

    #pull out special information (Timestamp, and frequency)
    epoch = float(df.columns[0])
    freq = df.iloc[0,0]
    data = df.iloc[1:, :].copy()  # the actual data are located from the second row
    

    #generate time column
    step = 1/freq
    time_col = pd.Series([epoch + i*step for i in range(data.shape[0])])
    time_col.name = 'time'
    

    #rename data column
    if colname == 'ACC':
        data.columns = ['x', 'y', 'z']
    else:
        data.columns = ['value']
        

    
    # merge time column and data
    ret_df = data.set_index(time_col)
    
    # z-score and remove outliers
    if colname == 'ACC':
        ret_df['zscore_x'] = zscore(ret_df.x)
        ret_df['zscore_y'] = zscore(ret_df.y)
        ret_df['zscore_z'] = zscore(ret_df.z)
        ret_df = ret_df[(ret_df.zscore_x.abs() < OUTLIER_THOLD) & (ret_df.zscore_y.abs() < OUTLIER_THOLD) & (ret_df.zscore_z.abs() < OUTLIER_THOLD)]

    else:
        ret_df['zscore'] = zscore(ret_df.value)     
        ret_df = ret_df[ret_df.zscore.abs() < OUTLIER_THOLD]


    # hi / lo pass decomp
    if colname == 'ACC':
        tonic, phasic = decompose_eda_signal(ret_df.zscore_x, freq)
        ret_df['tonic_x'] = tonic
        ret_df['phasic_x'] = phasic
        tonic, phasic = decompose_eda_signal(ret_df.zscore_y, freq)
        ret_df['tonic_y'] = tonic
        ret_df['phasic_y'] = phasic
        tonic, phasic = decompose_eda_signal(ret_df.zscore_z, freq)
        ret_df['tonic_z'] = tonic
        ret_df['phasic_z'] = phasic
        
    else:
        tonic, phasic = decompose_eda_signal(ret_df.zscore, freq)
        ret_df['tonic'] = tonic
        ret_df['phasic'] = phasic
    
    return ret_df.reset_index()


# IBI is a special case
# The first column's name is the epoch timestamp
# the data in that column are number of seconds elapsed since that time.
def add_time_ibi(df):
    epoch = float(df.columns[0])
    time_col = df.iloc[:, 0] + epoch
    time_col.name = 'time'
    
    ibi = df.iloc[:, 1]  #sometimes this column's name has an extra space in it.  that can throw off indexing
    ibi.name='value'   # this ensures a clean column name
    return pd.concat([time_col, ibi], axis=1)    
    

    
## Match timestamps on the bio markers to page times
def add_page_names(df, pid, pt_data):
    # Page Times for participant
    page_times = pt_data[pt_data.plab_short == pid].sort_values('tse')
    
    if page_times.shape[0] == 0:
        print(f"PageTime data does not contain id: {pid}")
        return

    df['page'] = ' '
    df['rnd'] = -99

    start_time = page_times.epoch_time_completed.iloc[0]
    
    # fill in landing page stuff
    df.loc[df.time < start_time, 'page'] = 'landing'
    
    for _, row in page_times.iloc[1:].iterrows():
        end_time = row.epoch_time_completed
        df.loc[(df.time > start_time) & (df.time <= end_time), 'page'] = row.page_name
        df.loc[(df.time > start_time) & (df.time <= end_time), 'rnd'] = row['round']
        
        start_time = row.epoch_time_completed
        
    return df[df.rnd != -99]  # ignore data that occurrs after the experiment

    

# For each participant....
# given a path to a participant's bio data
def process_participant(part_dir, part_label, pt_data):
    # the participant id is the directory name
    id = os.path.basename(part_dir)


    # Check if the participant is using a new for old empatica
    # In the old E4 data files, the EDA file is a single column
    try:
        eda = pd.read_csv(part_dir+"/EDA.csv")
        if len(list(eda)) != 1:
            print(f"Data format not old: {part_dir}")
            return
            
    except FileNotFoundError:
        print(f"Miss EDA.csv file in directory: {part_dir}")
        return


    # Ensure that the output directory exists
    Path(f"{BIO_TEMP_DIR}/{part_label}").mkdir(parents=True, exist_ok=True)

    # Open files and add timestamps
    for file_name in DATA_FILE_NAMES:
        try:
            df = pd.read_csv(f"{part_dir}/{file_name}.csv")
        
        except FileNotFoundError:
            print(f"Missing file in dir: {part_dir} - {file_name}")
            return
        except pandas.errors.EmptyDataError:
            print(f"EmptyDataError - {part_dir} - {file_name}")
            return

        # Special case for IBI
        if file_name == 'IBI':
            w_time = add_time_ibi(df)    
            pass
        else:
            w_time = add_time(df, file_name)
            
        w_page_names = add_page_names(w_time, id, pt_data)
        
        if w_page_names is not None:
            w_page_names.to_csv(f"{BIO_TEMP_DIR}/{part_label}/{file_name}.csv", index=False)


# Mulitprocessing stuff
def task(_iq):
    for args in iter(_iq.get, 'STOP'):
        process_participant(*args)
    


if __name__ == '__main__':
    #set_start_method('fork')
    
    print("###\n###\n### Adding Timestamps and Page Label to Biometric Data")
    
    args, pt_data = set_up()

    m = Manager()
    iq = m.Queue()
    num_tasks = 0
    retrieved = 0
    
    procs = [Process(target=task, args=[iq]) for _ in range(cpu_count())]
    for p in procs: p.start()
    for dir, part_lab in args:
        iq.put([dir, part_lab, pt_data])
        num_tasks += 1
    for _ in range(cpu_count()):iq.put('STOP')
    for p in procs: p.join()
    

    
# args, pt_data = set_up(skip=False)
# d, pid  = args[14]
# process_participant(d, pid, pt_data)