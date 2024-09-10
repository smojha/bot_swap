import pandas as pd
import glob
import os
from scipy.stats import zscore
from pathlib import Path
import pandas.io.common
from multiprocessing import Process, Manager, cpu_count #, set_start_method
import sys
from avro.datafile import DataFileReader
from avro.io import DatumReader


if 'Preproc/code' not in sys.path:
    sys.path.insert(0, 'Preproc/code')

from bio_preproc_funcs import decompose_eda_signal


BIO_TEMP_DIR = 'Preproc/temp/bio/page_merge'
TEMP_DIR = 'Preproc/temp'
BIO_SOURCE_DIR = 'Raw_Data/bio_data'
DATA_FILE_NAMES = ['ACC', 'BVP', 'EDA', 'HR', 'IBI', 'TEMP']
OUTLIER_THOLD = 2.5


## The directory that stores the biometric data has the name of the 3-digit code of the participant
## The actual participant lable is <sessioin_code>_<3-digit_code>.  This function will extract
# the 3-digit code from the participant directory and look up the full partiipant code form the
# given participant directory. 
def get_part_label_for_dir(part_dir, part_data):
    # the participant id is the directory name
    _3d_id = os.path.basename(part_dir)
    
    #some bio folders refer to non-existent ids, skip them
    if part_data[part_data.plab_short == _3d_id].shape[0] == 0:
        print(f"Id in bio data not in experiment data: {part_dir}")
        return

    #The set_up function should have already checked for duplicate ids
    # So we, just roll with it here and return the first one we find.
    part_label = part_data[part_data.plab_short == _3d_id].part_label.values[0]


    # find session
    #parent_dir = os.path.basename(os.path.dirname(part_dir)) # the parent directory name contains the session date
    #date_of_session = "20" + parent_dir[-8:].replace("_", "-") # turn parent directory name into label stored in session data
    #sess = sess_data.loc[date_of_session].session # use the label to get the session code.  
    
    return part_label


## Overhead tasks. Protect this with a function so processes don't re-run this stuff
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
        print("WARNING:  Found duplicate ids")
        print(dups)
        
    # Reduce the page time data to in-lab participants and add a shorteded part_label
    pt_data = pt_data.set_index('part_label').loc[part_data.part_label]
    pt_data = pt_data.join(part_data.set_index('part_label').plab_short)
    
    #We are currently using the epoch timestamp.  Treating time information as a number
    # is more efficient.  Thus, we do not need to convert these now.
    #pt_data['tse'] = pt_data.tse.apply(pd.Timestamp)
    
    
    # Generate a list of directoies, filtering out ineligible directory names
    dirs = [f for f in glob.glob(f"{BIO_SOURCE_DIR}/Hybrid_*/*") if len(os.path.basename(f)) == 3]
    
    # Pair a participant directory with a full part_label.  
    args = [(d, get_part_label_for_dir(d, part_data)) for d in dirs]
    
    # Skip participants that already exist in the BIO_TEMP_DIR folder.
    # This is a return object.
    args_to_keep = []
    for part_dir, part_label in args:
        
        if part_label is None:
            continue
            
        #Test if the directory exists already
        if os.path.exists(f"{BIO_TEMP_DIR}/{part_label}") and skip:
            print(f"Folder exists - {part_label}.   Skipping")
        
        else:
            args_to_keep.append((part_dir, part_label))
    
    
    #Ensure that the  output dir exists
    Path(BIO_TEMP_DIR).mkdir(parents=True, exist_ok=True)
    
    return args_to_keep, pt_data


# Add time column.
# Most data are formatted as the column names are the start time as number of seconds since the epoch
# The second row contains the frequency of the data
# the rest of the rows are the measurements.
#
# We are z-scoring and filtering out outliiers So for bio markers that collect measurments in
# multiple dimensions, we need to index the returned data frame by timestamp.
def add_time(time_series, epoch, freq, include_time=True):
    
    data = pd.Series(time_series)
    data.name = 'value'

    #generate time column
    if include_time:
        step = 1/freq
        time_col = pd.Series([epoch + i*step for i in range(len(data))])
        time_col.name = 'time'
                
        # merge time column and data
        df = pd.concat([time_col, data], axis='columns')
    else:
        df = data.to_frame()

    df['zscore'] = zscore(df.value)     
    #df = df[df.zscore.abs() < OUTLIER_THOLD]
    
    if df.shape[0] < 19:
        return


    # hi / lo pass decomp
    tonic, phasic = decompose_eda_signal(df.zscore, freq)
    df['tonic'] = tonic
    df['phasic'] = phasic
    
    # Setting the index to 'time'
    # This ensures that if these time series needs to be combined with others (ACC)
    # That they will properly align
    return df.set_index('time')


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
        print(f"\t - PageTime data does not contain id: {pid}")
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



#Process the old-style files
def process_old(part_dir, part_label, pt_data):
    print(f"\tProcessing Old Device: {part_label}")
    # the participant pid is the directory name
    pid = os.path.basename(part_dir)

    # Open files and add timestamps
    for file_name in DATA_FILE_NAMES:
        try:
            df = pd.read_csv(f"{part_dir}/{file_name}.csv")
        
        except FileNotFoundError:
            print(f"\t\t - Missing file in dir: {part_dir} - {file_name}")
            return
        except pandas.errors.EmptyDataError:
            print(f"\t\t - EmptyDataError - {part_dir} - {file_name}")
            return
        
        try:
            epoch = float(df.columns[0])
        except ValueError:
            print(f"Value Error in process_old: {part_dir}, {part_label}")
            raise
        freq = df.iloc[0,-1]
        time_series = df.iloc[1:, :]
        
            
        if freq == 0:
            print (f"\t\t - Zero frequency detected. {part_dir} - {part_label} {file_name}")
            return
    
        # Special case for IBI
        if file_name == 'IBI':
            w_time = add_time_ibi(df)    
            pass
        
        elif file_name == 'ACC':
            t_series = df.iloc[:, 0]
            x = add_time(t_series, epoch, freq)
            x.columns = ['x', 'x_zscore', 'x_tonic', 'x_phasic']
            
            t_series = df.iloc[:, 0]
            y = add_time(t_series, epoch, freq)
            y.columns = ['y', 'y_zscore', 'y_tonic', 'y_phasic']
            
            t_series = df.iloc[:, 0]
            z = add_time(t_series, epoch, freq)
            z.columns = ['z', 'z_zscore', 'z_tonic', 'z_phasic']
            
            # The x,y,z data frames are indexed by timestamp
            # This ensures that they line up on time.
            w_time = pd.concat([x,y,z], axis='columns').reset_index()
            
        else:
            # These are the typical file.  TEMP, HR, EDA, BVP
            w_time = add_time(time_series.iloc[:,0].values, epoch, freq).reset_index()
    
        # Add the page names
        w_page_names = add_page_names(w_time, pid, pt_data)
        
        if w_page_names is not None:
            w_page_names.to_csv(f"{BIO_TEMP_DIR}/{part_label}/{file_name}.csv", index=False)


def read_avro(avro_file_path):
    try:
        with open(avro_file_path, 'rb') as avro_file:
            reader = DataFileReader(avro_file, DatumReader())
            data = next(reader)
            return data
    
    except Exception as e:
        print(f"Error processing file {avro_file_path}: {e}")


def get_bio_marker_for_tag_xyz(data, data_tag):
    # accelerometer
    raw_data = data["rawData"][data_tag]
    x = raw_data["x"]
    y = raw_data["y"]
    z = raw_data["z"]
        
    freq = raw_data["samplingFrequency"]
    #check for 0 freqency files
    if freq == 0:
        return None
    

    epoch = raw_data["timestampStart"] / 1e6
    x_w_time = add_time(x, epoch, freq)
    x_w_time.columns = ['x', 'x_zscore', 'x_tonic', 'x_phasic']
    
    y_w_time = add_time(y, epoch, freq)
    y_w_time.columns = ['y', 'y_zscore', 'y_tonic', 'y_phasic']
    
    z_w_time = add_time(z, epoch, freq)
    z_w_time.columns = ['z', 'z_zscore', 'z_tonic', 'z_phasic']

    data_combined = pd.concat([x_w_time, y_w_time, z_w_time], axis='columns')
    return data_combined.reset_index()

    
def get_bio_marker_for_tag(data, data_tag):
    raw_data = data["rawData"][data_tag]
    freq = raw_data["samplingFrequency"]
    #check for 0 freqency files
    if freq == 0:
        return None, "freq0"
    
    epoch = raw_data["timestampStart"] / 1e6
    data_w_time = add_time(raw_data["values"], epoch, freq)
    if data_w_time is None:
        return None, "emptyts"
    
    return data_w_time.reset_index(), None



##
## Process the new style data file (*.avro)
## 
def process_new(part_dir, part_label, pt_data):
    print(f"\tProcessing New Device: {part_label}")
    # the participant pid is the directory name
    pid = os.path.basename(part_dir)
    
    avro_files = glob.glob(os.path.join(part_dir, '*.avro'))
    avro_data_sets = [read_avro(f) for f in avro_files]
    avro_data_sets = [d for d in avro_data_sets if d is not None]

    # data containers
    accelerometer_data = []
    # gyroscope_data = []
    eda_data = []
    temperature_data = []
    bvp_data = []
    # systolic_peaks_data = []
    steps_data = []
    # tags_data = []

    # process each avro file
    for data in avro_data_sets:
    
        # accelerometer
        acc_w_time = get_bio_marker_for_tag_xyz(data, 'accelerometer')
        if acc_w_time is None:
            print (f"\t\t - Zero frequency detected. {part_dir} - {part_label} - accelerometer")
           
        accelerometer_data.append(acc_w_time)
        
        # gyroscope
        # gyro_w_time = get_bio_marker_for_tag_xyz(data, 'gyroscope', False)
        # gyroscope_data.append(gyro_w_time)
        
        markers = [
            (eda_data, 'eda'),
            (temperature_data, 'temperature'),
            (bvp_data, 'bvp'),
            (steps_data, 'steps'),
            # (tags_data, 'tags'),
        ]
        
        for accumulator, tag in markers:            
            data_for_tag, error_code = get_bio_marker_for_tag(data, tag)
            if error_code == 'freq0':
                print (f"\t\t - Zero frequency detected. {part_dir} - {part_label} - {tag}")
                
            elif error_code == 'emptyts':
                print (f"\t\t - Empty data for tag.  (likely it is too short for spectral decomp) {part_dir} - {part_label} - {tag} ")
                        
            else:
                accumulator.append(data_for_tag)
            
    
        # # systolic peaks
        # sps = data["rawData"]["systolicPeaks"]
        # for sp in sps["peaksTimeNanos"]:
        #     systolic_peaks_data.append([sp])
                
    acc_df = pd.concat(accelerometer_data).sort_values('time')
    # gyro_df = pd.concat(gyroscope_data).sort_values('time')
    eda_df = pd.concat(eda_data).sort_values('time')
    temp_df = pd.concat(temperature_data).sort_values('time')
    bvp_df = pd.concat(bvp_data).sort_values('time')
    
    steps_df = None
    if len(steps_data) > 0:
        steps_df = pd.concat(steps_data).sort_values('time')
    # tags_df = pd.concat(tags_data).sort_values('time')
 
    data_w_filenames = [
    (acc_df, 'ACC'),
    # (gyro_df, 'GYRO'),
    (eda_df, 'EDA'),
    (temp_df, 'TEMP'),
    (bvp_df, 'BVP'),
    (steps_df, 'STEPS'),
    # (tags_df, 'TAGS'),
    ]
 

    for df, fn in data_w_filenames:
        if df is None:
            print(f"\t\t - No data for: {fn}. Skipping.  Likely not enough data points for decomp.")
            continue
        df_w_page = add_page_names(df, pid, pt_data)
        if df_w_page is not None:
            df_w_page.to_csv(f"{BIO_TEMP_DIR}/{part_label}/{fn}.csv", index=False)


# For each participant....
# given a path to a participant's bio data
def process_participant(part_dir, part_label, pt_data):
    
    # Ensure that the output directory exists
    Path(f"{BIO_TEMP_DIR}/{part_label}").mkdir(parents=True, exist_ok=True)
    
    # Check if the participant is using a new for old empatica
    # In the old E4 data files, the EDA file is a single column
    # new devices have avro files
    is_new = len(list(glob.glob(f"{part_dir}/*.avro"))) > 0

   # Process files
    if is_new:
        process_new(part_dir, part_label, pt_data)
    else:
        process_old(part_dir, part_label, pt_data)
        
            


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
    

    
# args, pg = set_up(skip=False)
# d, pl = ('Raw_Data/bio_data/Hybrid_24_07_15/52W', 'pdqr3ms5_52W')

# def is_it_new(d):
#     return len(list(glob.glob(f"{d}/*.avro"))) > 0
# new_ones = [a for a in args if is_it_new(a[0])]
# d, pl = new_ones[0]

# pid = os.path.basename(d)
# avro_files = glob.glob(os.path.join(d, '*.avro'))
# avro_data_sets = [read_avro(f) for f in avro_files]
# avro_data_sets = [d for d in avro_data_sets if d is not None]

# a = get_bio_marker_for_tag_xyz(avro_data_sets[0], 'accelerometer')




# for d, pl in new_ones[2:]:
#     process_participant(d, pl, pg)