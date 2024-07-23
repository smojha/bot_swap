import pandas as pd
import glob
import os
from pathlib import Path
import pandas.io.common
from multiprocessing import Process, Manager, cpu_count, set_start_method
import pytz
import datetime


BIO_TEMP_DIR = 'Preproc/temp/bio'
TEMP_DIR = 'Preproc/temp'
BIO_SOURCE_DIR = 'Data/EDA_data'

sess_data = pd.read_csv(f"{TEMP_DIR}/preproc_session.csv").set_index('label')
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

DATA_FILE_NAMES = ['ACC', 'BVP', 'EDA', 'HR', 'IBI', 'TEMP']
EAST_COAST_TZ = pytz.timezone('America/New_York')
ONE_MILLION = 1000000

#Make output dir
Path(BIO_TEMP_DIR).mkdir(parents=True, exist_ok=True)


# Add time column.
# Most data are formatted as the column names are the start time as number of seconds since the epoch
# The second row contains the frequency of the data
# the rest of the rows are the measurements.
def add_time(df, colname):

    #pull out special information (Timestamp, and frequency)
    epoch = float(df.columns[0])
    freq = df.iloc[0,0]
    data = df.iloc[1:, :]  # the actual data are located from the second row
    

    #generate time column
    delta = datetime.timedelta(microseconds=ONE_MILLION/freq)
    dt = datetime.datetime.fromtimestamp(epoch, tz=EAST_COAST_TZ)
    time_col = pd.date_range(start=dt, periods=data.shape[0], freq=delta)
    time_col.name = 'time'

    #rename data column
    if colname == 'ACC':
        data.columns = ['ACC_x', 'ACC_y', 'ACC_z']
    else:
        data = data.rename(mapper=lambda x: colname, axis='columns')
    
    data.set_index(time_col, inplace=True)
    
    return data.reset_index()


# IBI is a special case
# The first column's name is the epoch timestamp
# the data in that column are number of seconds elapsed since that time.
def add_time_ibi(df):
    epoch = float(df.columns[0])
    dt = datetime.datetime.fromtimestamp(epoch, tz=EAST_COAST_TZ)  # start time
    get_ts = lambda x: dt + datetime.timedelta(seconds=x)   # value given in the number of seconds elapsed since the start time.
    time_col = df.iloc[:, 0].apply(get_ts) # generate timestamps
    time_col.name = 'time'
    
    ibi = df.iloc[:, 1]  #sometimes this column's name has an extra space in it.  that can throw off indexing
    ibi.name='IBI'   # this ensures a clean column name
    return pd.concat([time_col, ibi], axis=1)    
    

    
## Match timestamps on the bio markers to page times
def add_page_names(df, pid):
    # Page Times for participant
    page_times = pt_data[pt_data.plab_short == pid].sort_values('tse')

    df['page'] = ' '
    df['rnd'] = -99

    
    start_time = page_times.tse.iloc[0]
    
    # fill in landing page stuff
    df.loc[df.time < start_time, 'page'] = 'landing'
    
    for _, row in page_times.iloc[1:].iterrows():
        end_time = row.tse
        df.loc[(df.time > start_time) & (df.time <= end_time), 'page'] = row.page_name
        df.loc[(df.time > start_time) & (df.time <= end_time), 'rnd'] = row['round']
        
        start_time = row.tse
        
    return df  

    

# For each participant....
# given a path to a participant's bio data
def process_participant(part_dir):
    # the participant id is the directory name
    id = os.path.basename(part_dir)
    
    #some bio folders refer to non-existent ids, skip them
    if part_data[part_data.plab_short == id].shape[0] == 0:
        print(f"Id in bio data not in experiment data: {id}")
        return
    part_label = part_data[part_data.plab_short == id].part_label.values[0]

    # find session
    parent_dir = os.path.basename(os.path.dirname(part_dir)) # the parent directory name contains the session date
    date_of_session = "20" + parent_dir[-8:].replace("_", "-") # turn parent directory name into label stored in session data
    sess = sess_data.loc[date_of_session].session # use the label to get the session code.

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
        else:
            w_time = add_time(df, file_name)
            
        w_page_names = add_page_names(w_time, id)
        
        w_time.to_csv(f"{BIO_TEMP_DIR}/{part_label}/{file_name}.csv", index=False)


# Mulitprocessing stuff
def task(_iq):
    for args in iter(_iq.get, 'STOP'):
        process_participant(*args)
    


if __name__ == '__main__':
    #set_start_method('fork')

    m = Manager()
    iq = m.Queue()
    num_tasks = 0
    retrieved = 0
    
    procs = [Process(target=task, args=[iq]) for _ in range(cpu_count())]
    for p in procs: p.start()
    for dir in dirs:
        iq.put([dir])
        num_tasks += 1
    for _ in range(cpu_count()):iq.put('STOP')
    for p in procs: p.join()
    

    

#process_participant(dirs[10])