import pandas as pd

print("\n##########")
print("## Preproc Session")


TEMP_DIR = 'Preproc/temp'
sess_data = pd.read_csv(f'{TEMP_DIR}/normalized_session.csv').set_index('session')
group_data = pd.read_csv(f'{TEMP_DIR}/normalized_group.csv')
player_data = pd.read_csv(f'{TEMP_DIR}/normalized_player.csv')

n = player_data.groupby(['session', 'round']).id_in_group.count().groupby('session').max()
n.name = 'n'
flt = group_data.groupby(['session'])['float'].max()
flt.name = 'flt'

sess_data = sess_data.join(n).join(flt)

sess_data.to_csv(f'{TEMP_DIR}/preproc_session.csv')
