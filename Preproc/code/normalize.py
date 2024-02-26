import pandas as pd
import re
from pathlib import Path
import os


DATA_DIR = 'Data'
TEMP_DIR = 'Preproc/temp'

def get_df(base):
    paths =  Path(DATA_DIR).rglob(f'{base}*.csv')
    dfs =  [pd.read_csv(p) for p in paths]
    concat = pd.concat(dfs)
    return concat


common_map={'session.code': 'session'
            , 'subsession.round_number': 'round'
            , 'participant.code': 'participant'}

def remove_non_part(df, page_name='NonParticipantPage'):
    return df[df['participant._current_page_name'] != page_name].copy()

def get_variables(start, df, include_rounds=False, include_participant=False):
    names = list(filter(lambda x: x.startswith(start), df))
    if 'session' not in names:
        names = ['session'] + names

    if include_rounds:
        names.insert(1, 'round')
    if include_participant:
        names.insert(1,'participant')

    filtered_df = df[names].copy()
    filtered_df.rename(mapper=lambda x: re.sub('.*\.', '', x), axis=1, inplace=True)
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
#rounds_data.drop(, axis=1, inplace=True)

# Participant Data
print("... Participants")
part_data = get_variables('participant', rounds_data)

# Session Data
print("... Sessions")
sess_data = get_variables('session', rounds_data)
sess_data.dropna(axis=1, how='all', inplace=True)
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
orders_data.drop(['market_price', 'volume', 'part_label'], axis=1, inplace=True)
orders_data.rename({'round_number': 'round'}, axis=1, inplace=True)
orders_data.drop(['original_quantity', 'automatic'], axis='columns', inplace=True)


#%% md
# Payment
#%%
print("... Payment")
payment_data = get_df('payment')

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



#############################
# write out data to temp director
print("Writing normalized data to disk")

#part_data = part_data[list(part_data)[:-2]]
part_data.to_csv(f"{TEMP_DIR}/normalized_part.csv", index=None)
sess_data.to_csv(f"{TEMP_DIR}/normalized_session.csv", index=None)
player_data.to_csv(f"{TEMP_DIR}/normalized_player.csv", index=None)
group_data.to_csv(f"{TEMP_DIR}/normalized_group.csv", index=None)
orders_data.to_csv(f"{TEMP_DIR}/normalized_orders.csv", index=None)



# for c in part_data:
#     print ("Casting ", c, part_data[c].dtype.kind)
#     v= part_data[c].values.astype(str)
#
# a = part_data['mturk_assignment_id'].isna()
# print("mturk_assignment_id: ", part_data['mturk_assignment_id'].dtype)
# print(part_data['mturk_assignment_id'])