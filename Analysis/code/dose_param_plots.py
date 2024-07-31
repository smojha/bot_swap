import pandas as pd
import matplotlib.pyplot as plt
import sys

# if 'Analysis/code' not in sys.path:
#     sys.path.insert(0, 'Analysis/code')
   
# from SessionPlotter import SessionPlotter, SessionPlotModifier

# print("\n##################")
# print("## Generate DOSE param plots")

INPUT_DIR = 'Analysis/input'
TEMP_DIR = 'Analysis/temp'

group_data = pd.read_csv(f'{INPUT_DIR}/group.csv')
player_data = pd.read_csv(f'{INPUT_DIR}/player.csv')#.set_index(['session', 'part_label'])
sess_data = pd.read_csv(f'{INPUT_DIR}/session.csv').set_index('session')
part_data = pd.read_csv(f'{INPUT_DIR}/participant.csv')



def z_score_dose(player_df):
    mu_avg = player_df.dose_mu.mean()
    mu_std = player_df.dose_mu.std()
    mu_z = (player_df.dose_mu - mu_avg) / mu_std
    mu_z.name = "mu_z"
    
    r_avg = player_df.dose_r.mean()
    r_std = player_df.dose_r.std()
    r_z = (player_df.dose_r - r_avg) / r_std
    r_z.name = "r_z"
    
    return pd.concat([player_df['round'], mu_z, r_z], axis='columns').set_index('round')
    
    
z_scores = player_data.groupby('part_label').apply(z_score_dose)
z_scores_prev = z_scores.groupby(level=0).shift(1)
zs = z_scores.join(z_scores_prev, rsuffix='_prev').dropna()

zs['mu_pct'] = (zs.mu_z - zs.mu_z_prev) / zs.mu_z_prev
zs['r_pct'] = (zs.r_z - zs.r_z_prev) / zs.r_z_prev

zs.reset_index(inplace=True)

zs = zs.join(player_data.set_index(['part_label', 'round']).session, on=['part_label', 'round'])
zs.set_index(['session', 'round'], inplace=True)
zs2 = zs.join(group_data.set_index(['session', 'round']).rnd_returns)

zs2.plot.scatter('rnd_returns', 'r_z')

by_part_rnd = zs2.reset_index().set_index(['part_label', 'round'])
by_part_rnd.loc['kfzc0i99_59A'][['mu_z', 'r_z']].plot()

p = player_data.set_index('part_label')
p.loc['kfzc0i99_59A'][['dose_mu', 'dose_r']].plot()

# # Callback for title
# def title_for_r(sess):
#     s = sess_data.loc[sess]
#     return f"DOSE - r {s.label} (N={s.n}; Float={s.flt})"

# def title_for_mu(sess):
#     s = sess_data.loc[sess]
#     return f"DOSE - μ {s.label} (N={s.n}; Float={s.flt})"




# #Callback to get session modifier
# class Dose_Modifier(SessionPlotModifier):
#     def __init__(self, session, var):
#         self.session = session
#         self.var = var
        
#     def modify(self, plot):
#         s_data = player_data.loc[self.session]
#         is_first = True
#         participants = set(player_data.loc[self.session].index.values)
#         plot2 = plot.twinx()

#         for part in participants:
#             part_data = s_data.loc[part]
#             y = part_data[self.var]
#             x = part_data['round']
            
#             mean = y.mean()
#             std = y.std()
#             y = (y - mean)/std
            
            
#             lab = "r (z-scored)" if is_first else None
#             plot2.plot(x, y, color='lightgray', label=lab)

#             is_first = False
                
#         plot2.legend()

# mod_for_r = lambda s: Dose_Modifier(s, 'dose_r')
# mod_for_mu = lambda s: Dose_Modifier(s, 'dose_mu')



# #Plot Sessions
# sp = SessionPlotter(group_data, mod_cb=mod_for_r, title_cb=title_for_r)
# sp.plot_sessions()
# sp.save_figures(TEMP_DIR, 'dose_r')

# sp = SessionPlotter(group_data, mod_cb=mod_for_mu, title_cb=title_for_mu)
# sp.plot_sessions()
# sp.save_figures(TEMP_DIR, 'dose_mu')



# group_data.set_index(['session', 'round'], inplace=True)
# price_diff = (group_data.price - group_data.prev_price).dropna()
# price_diff.name = 'price_change'

# player_data = player_data.reset_index().join(price_diff, on=['session', 'round'])

# #player_data.plot.scatter('price_change', 'dose_mu')


# #player_data.groupby(['price_change']).dose_r.mean().plot()
# #player_data.groupby(['price_change']).dose_mu.mean().plot()

# quant = part_data.market_bonus.quantile(.2)
# high_earners = part_data[part_data.market_bonus <= quant].part_label

# hpd = player_data[player_data.part_label.isin(high_earners)]
# #hpd.groupby(['price_change']).dose_mu.mean().plot()



# p = player_data.set_index(['session', 'round'])[['dose_r', 'dose_mu']]

# dose_data = p.join(group_data.rnd_returns)
