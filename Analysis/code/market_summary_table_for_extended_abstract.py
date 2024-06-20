import pandas as pd

print ("## Generating Market Summary Table for Extended Abract")

INPUT_DIR = "Analysis/input"
TEX_DIR = "Analysis/temp/tex"

sess_data = pd.read_csv(f"{INPUT_DIR}/session.csv").set_index('session')
part_data = pd.read_csv(f"{INPUT_DIR}/participant.csv").set_index(['session', 'part_label'])
group_data = pd.read_csv(f"{INPUT_DIR}/group.csv").set_index(['session', 'round'])
player_data = pd.read_csv(f"{INPUT_DIR}/player.csv").set_index(['part_label', 'round'])

pcounts = pd.pivot_table(part_data, values='showup', index='session', columns='site', aggfunc="count")

avg_price = group_data.groupby('session').price.mean()
avg_price.name = "avg_price"
avg_vol = group_data.groupby('session').volume.mean()
max_price = group_data.groupby('session').price.max()

#Which Markets Crashed
a = group_data.reset_index()
b = a[a['round'] == 30].copy()
b['crash'] = b.price < 20
crash = b[['session', 'crash']].set_index('session')

# Forecasts
def get_fcast_dev(row, f_idx=0):
    f_col = f'f{f_idx}'
    f_rnd_key = f'fcast_rnd_{f_idx}'
    f_rnd = row[f_rnd_key]
    if pd.isna(f_rnd):
        return None
    actual_price = group_data.loc[(row.session, f_rnd)].price
    dev = row[f_col] - actual_price
    return dev

player_data['fcast_dev_0'] = player_data.apply(get_fcast_dev, axis='columns', f_idx=0)
player_data['fcast_dev_2'] = player_data.apply(get_fcast_dev, axis='columns', f_idx=1)
player_data['fcast_dev_5'] = player_data.apply(get_fcast_dev, axis='columns', f_idx=2)
player_data['fcast_dev_10'] = player_data.apply(get_fcast_dev, axis='columns', f_idx=3)

avg_dev = player_data.groupby('session')[['fcast_dev_0', 'fcast_dev_2', 'fcast_dev_5', 'fcast_dev_10' ]].mean()

#Join ing
tab = sess_data.label.to_frame().join(avg_price).join(avg_vol).join(max_price).join(crash).join(avg_dev).join(pcounts)
tab = tab.sort_values('label')
tab = tab.iloc[:, 1:]

# Rearrange Indexes
tab.index = pd.Index(['Market 1', 'Market 2', 'Market 3', 'Market 4'])
c_idx = pd.MultiIndex.from_tuples([
                ('Avg. Price', ''),
                ('Avg. Volume', ''),
                ('Max Price', ''),
                ('Crashed', ''),
                ('Avg. Forecast Deviation', '0'),
                ('Avg. Forecast Deviation', '2'),
                ('Avg. Forecast Deviation', '5'),
                ('Avg. Forecast Deviation', '10'),
                ('No. Participants', 'Lab'),
                ('No. Participants', 'Prolific')
                ])
tab.columns=c_idx
fmt2 = '{:.2f}'
fmt0 = '{:d}'
tab.style.format(precision=2).to_latex(f"{TEX_DIR}/market_summary_extend_abstract.tex", hrules=True, sparse_columns=True, multicol_align='c')

