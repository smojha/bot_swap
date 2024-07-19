
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
dirs = [f for f in glob.glob(f"{BIO_SOURCE_DIR}/Hybrid_*/*") if len(os.path.basename(f)) == 3]

DATA_FILE_NAMES = ['ACC', 'BVP', 'EDA', 'HR', 'IBI', 'TEMP']
EAST_COAST_TZ = pytz.timezone('America/New_York')
ONE_MILLION = 1000000

#Make output dir
Path(BIO_TEMP_DIR).mkdir(parents=True, exist_ok=True)



def add_time(df, colname):

    #pull out special information (Timestamp, and frequency)
    epoch = float(df.columns[0])
    freq = df.iloc[0,0]
    data = df.iloc[1:, :]
    

    #generate time column
    delta = datetime.timedelta(microseconds=ONE_MILLION/freq)
    dt = datetime.datetime.fromtimestamp(epoch, tz=EAST_COAST_TZ)
    time_col = pd.date_range(start=dt, periods=data.shape[0], freq=delta)#.to_series().reset_index(drop=True)
    time_col.name = 'time'

    #rename data column
    if colname == 'ACC':
        data2 = df.copy()
        data2.columns = ['ACC_x', 'ACC_y', 'ACC_z']
    else:
        data2 = df.rename(mapper=lambda x: colname, axis='columns')
    
    data.set_index(time_col, inplace=True)
    
    return data


def process_participant(part_dir):
    id = os.path.basename(part_dir)

    # find session
    parent_dir = os.path.basename(os.path.dirname(part_dir)) # the parent directory name contains the session date
    date_of_session = "20" + parent_dir[-8:].replace("_", "-") # turn parent directory name into label stored in session data
    sess = sess_data.loc[date_of_session].session # use the label to get the session code.

    # Check if the participant is using a new for old empatica
    try:
        eda = pd.read_csv(part_dir+"/EDA.csv")
        if len(list(eda)) != 1:
            print(f"Data format not old: {part_dir}")
            return
            
    except FileNotFoundError:
        print(f"Miss EDA.csv file in directory: {part_dir}")
        return


    Path(f"{BIO_TEMP_DIR}/{id}").mkdir(parents=True, exist_ok=True)

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

        w_time = add_time(df, file_name)
        w_time.to_csv(f"{BIO_TEMP_DIR}/{id}/{file_name}.csv")



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
    

    

    