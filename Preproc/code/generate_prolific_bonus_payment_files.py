import pandas as pd


print ("##\n##\n## Generating Prolific Bonus Data")

TEMP_DIR = 'Preproc/temp'
PAYMENT_DIR = 'Preproc/temp/payments'

p = pd.read_csv(f'{TEMP_DIR}/preproc_participant.csv')
s = pd.read_csv(f'{TEMP_DIR}/preproc_session.csv').set_index('session')

#filter out the in-lab people and set the index to session
p = p[p.site == 'Prolific'].set_index('session')

# Remove the ".dup" from any duplicated participants
p['part_label_core'] = p.part_label.str.replace("_.*", "", regex=True)


#loop sessions and generate csv files
for sess in s.index.values:
    p4s = p.loc[sess]
    date = s.loc[sess, 'sess_date']

    p4s = p4s[['part_label_core', 'total_bonus']]
    p4s.to_csv(f'{PAYMENT_DIR}/session_{date}.csv', index=False, header=False)