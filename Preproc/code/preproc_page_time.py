import pandas as pd

TEMP_DIR = 'Preproc/temp'
page_time = pd.read_csv(f'{TEMP_DIR}/normalized_page_times.csv')
part_data = pd.read_csv(f'{TEMP_DIR}/preproc_participant.csv')


# Generate east coast timestamp
page_time['tse'] = pd.to_datetime(page_time.epoch_time_completed, unit='s', utc=True).dt.tz_convert('America/New_York')

# Generate west coast timestamp
page_time['tsw'] = pd.to_datetime(page_time.epoch_time_completed, unit='s', utc=True).dt.tz_convert('America/Los_Angeles')

# Match up the participant code in the page_time data with the participant label
code_and_lab = part_data[['participant', 'part_label']].set_index('participant')


#Join in the participant labels
pt_w_label = page_time.join(code_and_lab, on='participant_code')

# Reorder Columns so the label is toward the front of the data frame
cols = list(page_time)
s = pt_w_label.session
plab = pt_w_label.part_label
the_rest = pt_w_label[cols[2:]]
pt_w_label = pd.concat([s, plab, the_rest], axis='columns')


pt_w_label.to_csv(f'{TEMP_DIR}/preproc_page_time.csv', index=None)

