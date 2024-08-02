import pandas as pd
import re
from pathlib import Path


DATA_DIR = 'Raw_Data'
TEMP_DIR = 'Preproc/temp'

DUPLICATES = [
    ('56f9364e895094000c8f4967', 'txyy1leq'),
    ('5f7529755aaa0e1a6e804640', 'nhrerg4w'),
    ('651c4484ba17050f6b716614', '19jfynhh'),
    ('65a2bc0d60b1e46f4e1d3cc8', 'txyy1leq'),
    ('62cd43d66c2dd7ae9ab53ae7', '19jfynhh'),
    ('56f9364e895094000c8f4967', 'r0fz6tf4'),
    ('5f7529755aaa0e1a6e804640', 'ao7syclg'),
    ('6267c3d17f88988d0d787c7f', 'r46wgr8m'),
    ('62cd43d66c2dd7ae9ab53ae7', 'r46wgr8m'),
    ('651c4484ba17050f6b716614', 'r46wgr8m'),
    ('65a2bc0d60b1e46f4e1d3cc8', 'r0fz6tf4'),    
    ('5ed543442db0060a955d12e1', '100hm05f'),
    ('612962f44f151ddfd0298c52', '100hm05f'),
    ('62b0ff84054c6ca32f481c65', '100hm05f'),
    ('632b947efa9da6a9bde31f94', '100hm05f'),
    ('6654b7668e8642303bbc2fa7', '100hm05f'),   
    ('5ed543442db0060a955d12e1', '4y7q8j7q'),
    ('612962f44f151ddfd0298c52', '4y7q8j7q'),
    ('62b0ff84054c6ca32f481c65', '4y7q8j7q'),
    ('632b947efa9da6a9bde31f94', '4y7q8j7q'),
    ('6654b7668e8642303bbc2fa7', '4y7q8j7q'),    
    ('659daa1ed4e13d6428103c1f', '4vs1ljv7'),
    ('66601438206fb7fc6c48a81f', '4vs1ljv7'),
    ('6018a5c0e1600b187ccb8693', 'pmyan048'),    
]

def flag_duplicates(df):
    for pid, sess in DUPLICATES:
        df.loc[(df.part_label == pid) & (df.session == sess), 'part_label'] = f'{pid}_dup'


def get_df(base):
    paths =  Path(DATA_DIR).rglob(f'Hybrid*/{base}*.csv')
    dfs =  [pd.read_csv(p) for p in paths]
    concat = pd.concat(dfs)
    return concat


common_map={'session.code': 'session', 
            'subsession.round_number': 'round',
            'participant.label': 'part_label',
            'participant.code': 'participant'}

def remove_non_part(df, page_name='NonParticipantPage'):
    return df[df['participant._current_page_name'] != page_name].copy()

def get_variables(start, df, include_rounds=False, include_participant=False):
    names = list(filter(lambda x: x.startswith(start), df))
    if 'session' not in names:
        names = ['session'] + names

    if include_rounds:
        names.insert(1, 'round')
    if include_participant:
        names.insert(1,'part_label')

    filtered_df = df[names].copy()
    filtered_df.rename(mapper=lambda x: re.sub(".*\\.", '', x), axis=1, inplace=True)
    filtered_df.drop_duplicates(inplace=True)

    if 'role' in filtered_df:
        filtered_df.drop('role', axis=1, inplace=True)
    if 'payoff' in filtered_df:
        filtered_df.drop('payoff', axis=1, inplace=True)

    return filtered_df

print("Normalizing")

# Rounds Data
rounds_data = get_df('rounds')

rounds_data = remove_non_part(rounds_data)
rounds_data.rename(mapper=common_map, axis=1, inplace=True)
flag_duplicates(rounds_data)
#rounds_data.drop(, axis=1, inplace=True)

# Participant Data
print("... Participants")
part_data = get_variables('participant', rounds_data, include_participant=True)

# Session Data
print("... Sessions")
sess_data = get_variables('session', rounds_data)
sess_data.dropna(axis=1, how='all', inplace=True)
# Rename the label column to something that makes more sense in the context of how the column is used.
sess_data.rename(mapper={'label': 'sess_date'}, axis='columns', inplace=True)
sess_data.drop(['is_demo'], axis=1, inplace=True)

# Player Data
print("... Players")
player_data = get_variables('player', rounds_data, include_rounds=True, include_participant=True)

# Group Data
print("... Groups")
group_data = get_variables('group', rounds_data, include_rounds=True)
group_data.drop('id_in_subsession', axis=1, inplace=True)

#%% md
# Orders
#%%
print("... Orders")
orders_data = get_df('orders')
orders_data.drop(['market_price', 'volume'], axis=1, inplace=True)
orders_data.rename({'round_number': 'round'}, axis=1, inplace=True)
orders_data.rename({'round_number': 'round'}, axis=1, inplace=True)


#%% md
# Payment
#%%
print("... Payment")
payment_data = get_df('payment')
flag_duplicates(payment_data)


print("... Page Times")
page_time_data = get_df('PageTimes')
page_time_data.rename({'session_code': 'session'}, axis=1, inplace=True)
part_labels_by_code = part_data.set_index('participant').part_label
page_time_data = page_time_data.join(part_labels_by_code, on='participant_code')
flag_duplicates(page_time_data)

##
# Landing Data - Contains the quiz
##
landing_data = get_df('landingct')
landing_data.rename(mapper=common_map, axis=1, inplace=True)
flag_duplicates(landing_data)
landing_data = get_variables('player', landing_data, include_participant=True)

###############
# Validating sessions
# A cursory check of the data.  If any session is deemed to be incomplete or invalid
# we will remove it.
############

## Group Check.
## All group information in a valid session will have price and volume data for each round.
is_price_na = group_data.price.isna()
is_vol_na = group_data.volume.isna()
is_either_na = is_price_na | is_vol_na
is_either_na.name = 'na'
group_check_df = pd.concat([group_data.session, is_either_na], axis=1)

# Here we count up the number of rounds in each session with a null price or volume.
# a good session will sum to zero.
sessions_and_missing_count = group_check_df.groupby('session').sum()
good_sessions = sessions_and_missing_count[sessions_and_missing_count.na == 0].index.values
good_sessions

def keep_good_sessions(df, good):
    return df[df.session.isin(good)]

part_data = keep_good_sessions(part_data, good_sessions)
sess_data = keep_good_sessions(sess_data, good_sessions)
player_data = keep_good_sessions(player_data, good_sessions)
group_data = keep_good_sessions(group_data, good_sessions)
orders_data = keep_good_sessions(orders_data, good_sessions)
payment_data = keep_good_sessions(payment_data, good_sessions)
page_time_data = keep_good_sessions(page_time_data, good_sessions)

##  Don't run the landing through the good sessions filter.
## This is run in a separate session
#landing_data = keep_good_sessions(landing_data, good_sessions)


#############################
# write out data to temp director
print("Writing normalized data to disk")

#part_data = part_data[list(part_data)[:-2]]
part_data.to_csv(f"{TEMP_DIR}/normalized_part.csv", index=None)
sess_data.to_csv(f"{TEMP_DIR}/normalized_session.csv", index=None)
player_data.to_csv(f"{TEMP_DIR}/normalized_player.csv", index=None)
group_data.to_csv(f"{TEMP_DIR}/normalized_group.csv", index=None)
orders_data.to_csv(f"{TEMP_DIR}/normalized_orders.csv", index=None)
landing_data.to_csv(f"{TEMP_DIR}/normalized_landing.csv", index=None)
payment_data.to_csv(f"{TEMP_DIR}/normalized_payment.csv", index=None)
page_time_data.to_csv(f"{TEMP_DIR}/normalized_page_times.csv", index=None)

# for c in part_data:
#     print ("Casting ", c, part_data[c].dtype.kind)
#     v= part_data[c].values.astype(str)
#
# a = part_data['mturk_assignment_id'].isna()
# print("mturk_assignment_id: ", part_data['mturk_assignment_id'].dtype)
# print(part_data['mturk_assignment_id'])