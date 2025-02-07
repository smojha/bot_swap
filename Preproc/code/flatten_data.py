import pandas as pd

print("###\n###\n### Flattening Data")

TEMP_DIR = 'Preproc/temp'

#Read in experiment data
sess_data = pd.read_csv(f"{TEMP_DIR}/preproc_session.csv").set_index('session')
group_data = pd.read_csv(f"{TEMP_DIR}/preproc_group.csv").set_index(['session', 'round'])
part_data = pd.read_csv(f"{TEMP_DIR}/preproc_participant.csv").set_index(['session'])
player_data = pd.read_csv(f"{TEMP_DIR}/preproc_player.csv").set_index(['part_label', 'round'])


# Clean out some columns that will be duplicated in the join
player_columns = list(player_data)
for c in ['session']:
    player_columns.remove(c)
player_data = player_data[player_columns]

part_data.drop(['participant'], axis='columns', inplace=True)

## Joining exp data
a = group_data.join(sess_data, on='session')
a = a.join(part_data, on='session')
flat = a.join(player_data[player_columns], on=['part_label', 'round'])



#write to disk
flat.to_csv(f"{TEMP_DIR}/flattened_data.csv")

