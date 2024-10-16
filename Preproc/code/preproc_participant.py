
import pandas as pd

LAB_SHOWUP = 20

print("\n###############")
print("## Preprocessing participants")

TEMP_DIR = 'Preproc/temp'
part_data = pd.read_csv(f'{TEMP_DIR}/normalized_part.csv')
group_data = pd.read_csv(f'{TEMP_DIR}/normalized_group.csv')
player_data = pd.read_csv(f'{TEMP_DIR}/normalized_player.csv')
sess_data = pd.read_csv(f'{TEMP_DIR}/normalized_session.csv')
order_data = pd.read_csv(f'{TEMP_DIR}/preproc_orders.csv')
payment_data = pd.read_csv(f'{TEMP_DIR}/normalized_payment.csv').set_index('part_label')

# Keep 'participant'.   We need that to match page time data.
cols_to_drop = ['_is_bot', '_max_page_index', '_index_in_pages', '_current_page_name', '_current_app_name', 'visited', 'mturk_worker_id', 'mturk_assignment_id']

print("\t...Removing unnecessary columns")
part_data.drop(cols_to_drop, axis=1, inplace=True)

## Site Variable
print ("\t... Site variable")
is_lab =  part_data.part_label.str.len() < 25
part_data['site'] = 'Prolific'
part_data.loc[is_lab, 'site'] = 'Lab'


part_final =part_data
#%%

####
# Calculate Payouts
####
# TODO:   Remove this and place the payouts in the experiment sensibly.
print("\t...Joining Payouts")
cols=['clicked_button', 'market_bonus', 'forecast_bonus', 'risk_bonus', 'quiz_bonus', 'total_bonus', 'showup', 'total_payment']
part_final = part_final.join(payment_data[cols], on='part_label')

# Lab participants earn a payout of 20
part_final.loc[part_final.site == 'Lab', 'showup'] = LAB_SHOWUP
part_final.total_payment = part_final.showup + part_final.total_bonus


#########
##  Number of Trades
#########
attempted_trades = order_data.groupby('part_label').type.count()
attempted_trades.name = 'attempted_trades'
part_final = part_final.join(attempted_trades, on='part_label')

executed_trades = order_data[order_data.quantity_final > 0].groupby('part_label').type.count()
executed_trades.name = 'executed_trades'
part_final = part_final.join(executed_trades, on='part_label')


#drop unnecessary columns
to_drop = ['id_in_session', 'time_started_utc', 'clicked_button']
part_final.drop(to_drop, axis='columns', inplace=True)
#%% md

#%%
# b = ['quiz_1', 'quiz_2', 'quiz_3', 'quiz_4', 'five_years', 'one_year', 'stock_safer', 'bat_and_ball', 'widgets', 'lilies_on_lake']
# cols = []
# for c in b:
#     cols.append(c)
#     cols.append(f"{c}_score")
# part_final[cols]
#%%
# Write out to disk
print("Writing to disk")
part_final.to_csv(f'{TEMP_DIR}/preproc_participant.csv', index=False)

