import pandas as pd

print("\n#########")
print("Preprocessing Page Timings")

TEMP_DIR = 'Preproc/temp'
page_time = pd.read_csv(f'{TEMP_DIR}/normalized_page_times.csv')
part_data = pd.read_csv(f'{TEMP_DIR}/preproc_participant.csv')
group_data = pd.read_csv(f'{TEMP_DIR}/normalized_group.csv')

page_time.rename({'round_number': 'round'}, axis='columns', inplace=True)

# purging practice rounds
print("\t... Purging practice rounds")
group_data = group_data[group_data.is_practice == 0].copy()
np_rounds = group_data['round'].values
start_round = min(np_rounds)

page_time = page_time[(page_time.app_name != 'rounds') | (page_time['round'] >= start_round)].copy()
page_time['round'] = page_time['round'] - start_round + 1

print("\t... Converting timestamps")
# Generate east coast timestamp
page_time['tse'] = pd.to_datetime(page_time.epoch_time_completed, unit='s', utc=True).dt.tz_convert('America/New_York')

# Generate west coast timestamp
page_time['tsw'] = pd.to_datetime(page_time.epoch_time_completed, unit='s', utc=True).dt.tz_convert('America/Los_Angeles')

# Match up the participant code in the page_time data with the participant label
code_and_lab = part_data[['participant', 'part_label']].set_index('participant')


#Join in the participant labels
# the normalize script now adds in the participant label
#print("\t... Adding participant labels")
#pt_w_label = page_time.join(code_and_lab, on='participant_code')

# Reorder Columns so the label is toward the front of the data frame
cols = list(page_time)
s = page_time.session
plab = page_time.part_label
the_rest = page_time[cols[2:]]
page_time = pd.concat([s, plab, the_rest], axis='columns')


page_time.to_csv(f'{TEMP_DIR}/preproc_page_time.csv', index=None)

