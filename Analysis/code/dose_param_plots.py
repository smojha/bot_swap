import pandas as pd
import matplotlib.pyplot as plt
import sys

if 'Analysis/code' not in sys.path:
    sys.path.insert(0, 'Analysis/code')
   
from SessionPlotter import SessionPlotter, SessionPlotModifier

print("\n##################")
print("## Generate DOSE param plots")

INPUT_DIR = 'Analysis/input'
TEMP_DIR = 'Analysis/temp'

group_data = pd.read_csv(f'{INPUT_DIR}/group.csv')
player_data = pd.read_csv(f'{INPUT_DIR}/player.csv').set_index(['session', 'part_label'])
sess_data = pd.read_csv(f'{INPUT_DIR}/session.csv').set_index('session')
part_data = pd.read_csv(f'{INPUT_DIR}/participant.csv')


# Callback for title
def title_for_r(sess):
    s = sess_data.loc[sess]
    return f"DOSE - r {s.label} (N={s.n}; Float={s.flt})"

def title_for_mu(sess):
    s = sess_data.loc[sess]
    return f"DOSE - μ {s.label} (N={s.n}; Float={s.flt})"




#Callback to get session modifier
class Dose_Modifier(SessionPlotModifier):
    def __init__(self, session, var):
        self.session = session
        self.var = var
        
    def modify(self, plot):
        s_data = player_data.loc[self.session]
        is_first = True
        participants = set(player_data.loc[self.session].index.values)
        plot2 = plot.twinx()

        for part in participants:
            part_data = s_data.loc[part]
            y = part_data[self.var]
            x = part_data['round']
            
            mean = y.mean()
            std = y.std()
            y = (y - mean)/std
            
            
            lab = "r (z-scored)" if is_first else None
            plot2.plot(x, y, color='lightgray', label=lab)

            is_first = False
                
        plot2.legend()

mod_for_r = lambda s: Dose_Modifier(s, 'dose_r')
mod_for_mu = lambda s: Dose_Modifier(s, 'dose_mu')



#Plot Sessions
sp = SessionPlotter(group_data, mod_cb=mod_for_r, title_cb=title_for_r)
sp.plot_sessions()
sp.save_figures(TEMP_DIR, 'dose_r')

sp = SessionPlotter(group_data, mod_cb=mod_for_mu, title_cb=title_for_mu)
sp.plot_sessions()
sp.save_figures(TEMP_DIR, 'dose_mu')



group_data.set_index(['session', 'round'], inplace=True)
price_diff = (group_data.price - group_data.prev_price).dropna()
price_diff.name = 'price_change'

player_data = player_data.reset_index().join(price_diff, on=['session', 'round'])

#player_data.plot.scatter('price_change', 'dose_mu')


#player_data.groupby(['price_change']).dose_r.mean().plot()
#player_data.groupby(['price_change']).dose_mu.mean().plot()

quant = part_data.market_bonus.quantile(.2)
high_earners = part_data[part_data.market_bonus <= quant].part_label

hpd = player_data[player_data.part_label.isin(high_earners)]
#hpd.groupby(['price_change']).dose_mu.mean().plot()



p = player_data.set_index(['session', 'round'])[['dose_r', 'dose_mu']]

dose_data = p.join(group_data.rnd_returns)