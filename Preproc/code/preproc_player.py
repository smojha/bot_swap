
import pandas as pd
import numpy as np

TEMP_DIR = 'preproc/temp'

player_data = pd.read_csv(f'{TEMP_DIR}/intermed_player.csv')
group_data = pd.read_csv(f'{TEMP_DIR}/preproc_group.csv').set_index(['session', 'round'])


print("## Preproc Group - Player")

print("\t# Calculating Forecast Errors")

def get_forecast_error(row, offset=0):
    f = row[f'f{offset}']
    if np.isnan(f):
        return None
    
    f_rnd = row[f'fcast_rnd_{offset}']
    sess = row['session']
    actual_price = group_data.loc[(sess, f_rnd), 'price']
    
    return actual_price - f

f0_error = player_data.apply(get_forecast_error, axis='columns', offset=0)
f1_error = player_data.apply(get_forecast_error, axis='columns', offset=1)
f2_error = player_data.apply(get_forecast_error, axis='columns', offset=2)
f3_error = player_data.apply(get_forecast_error, axis='columns', offset=3)

#index where we want to start inserting the forecast error columns
idx = list(player_data).index('fcast_rnd_3') + 1
player_data.insert(idx, 'fcast_err_0', f0_error)
player_data.insert(idx+1, 'fcast_err_1', f1_error)
player_data.insert(idx+2, 'fcast_err_2', f2_error)
player_data.insert(idx+3, 'fcast_err_3', f3_error)


#write back out to file
player_data.to_csv(f"{TEMP_DIR}/preproc_player.csv", index=False)

