import pandas as pd
import numpy as np

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


print("\n#########")
print("## Calculating Bubble Metrics")

FUND_VAL = 14

# Relative Absolute Deviation (RAD)
tot_vol = group_data.groupby('session').volume.sum()
price_as_pct = (group_data.price - 14)/14
price_as_pct_abs = np.abs(price_as_pct)

pv_abs = price_as_pct_abs * group_data.volume
pv_abs.name = 'pv'
pv_and_sess = pd.concat([group_data.session, pv_abs], axis=1)
pv_sum = pv_and_sess.groupby('session').pv.sum()

RAD = pv_sum / tot_vol
RAD.name = 'rad'

# Relative Deviation (RD)
pv = price_as_pct * group_data.volume
pv.name = 'pv'
pv_and_sess = pd.concat([group_data.session, pv], axis=1)
pv_sum = pv_and_sess.groupby('session').pv.sum()

RD = pv_sum / tot_vol
RD.name = 'rd'


# Average Bias (AB)
bias = group_data.price - FUND_VAL
bias.name = 'bias'
bias_and_sess = pd.concat([group_data.session, bias], axis=1)

AB = bias_and_sess.groupby('session').bias.mean()

# Total Dispersion
disp = np.abs(group_data.price - FUND_VAL)
disp.name = 'disp'
disp_and_sess = pd.concat([group_data.session, disp], axis=1)

TD = disp_and_sess.groupby('session').disp.sum()

# Price Amplitude (PA)
min_max_bias = bias_and_sess.groupby('session').bias.agg(['min', 'max'])
PA = min_max_bias['max'] - min_max_bias['min']
PA.name = 'pa'

# Duration
def get_duration(prices):
    """
    Calculate the duration of a single set of prices.
    """
    streaks = []
    curr_streak = 0
    for i in prices.price > prices.prev_price:
        if i:
            curr_streak += 1
        else:
            streaks.append(curr_streak)
            curr_streak = 0

    duration = max(streaks)
    return duration

durs = []
sessions = []
for sess in group_data.session.unique():
    p = group_data[group_data.session == sess].copy()
    p['prev_price'] = p.price.shift(1)
    durs.append(get_duration(p[['price', 'prev_price']]))
    sessions.append(sess)

DUR = pd.Series(durs, index=pd.Index(sessions, name='session'), name='dur')
# End Duration

#Put it all together
metrics = pd.concat([RAD,  AB, TD, PA, DUR], axis=1)


print("\t... Adding bubble metrics")
sess_data = sess_data.join(metrics)


print("\t... Finding market peaks")
peaks = group_data.groupby('session').price.max()
peaks.name = 'peak_price'

def get_peak_round(df):
    idx = df.set_index('round').price.argmax()
    return df['round'].iloc[idx]
max_round = group_data.groupby('session').apply(get_peak_round)
max_round.name = 'peak_round'

sess_data = sess_data.join(peaks)
sess_data = sess_data.join(max_round)

sess_data.to_csv(f'{TEMP_DIR}/preproc_session.csv')
