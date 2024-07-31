import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

print("## Generating Forecast Plots")

if 'Analysis/code' not in sys.path:
    sys.path.insert(0, 'Analysis/code')
   
from SessionPlotter import SessionPlotter, SessionPlotModifier



INPUT_DIR = 'Analysis/input'
IMG_DIR = 'Analysis/temp/img'


group_data = pd.read_csv(f'{INPUT_DIR}/group.csv')
player_data = pd.read_csv(f'{INPUT_DIR}/player.csv')
sess_data = pd.read_csv(f'{INPUT_DIR}/session.csv').set_index('session')


## Consolidate Forecast Data
p_grp = player_data.groupby(['session', 'round'])
f_means = p_grp[['pl_f0', 'pl_f1', 'pl_f2', 'pl_f3']].mean()
t_rnd = p_grp[['pl_fcast_rnd_0', 'pl_fcast_rnd_1', 'pl_fcast_rnd_2', 'pl_fcast_rnd_3']].max()

forecast = f_means.join(t_rnd)


#Callback to get session modifier
class ForecastModifier(SessionPlotModifier):
    def __init__(self, session):
        self.session = session
        
    def modify(self, plot):
        f_data = forecast.loc[self.session]
        is_first = True
        for _, row in f_data.iterrows():
            y = [ row.pl_f0, row.pl_f1, row.pl_f2, row.pl_f3 ]
            x = [ row.pl_fcast_rnd_0, row.pl_fcast_rnd_1,
                 row.pl_fcast_rnd_2, row.pl_fcast_rnd_3 ]
            
            f_lab = "Forecasts" if is_first else None
            plot.plot(x, y, color='lightgray', label=f_lab)
            
            dot_lab = "Current period forecast" if is_first else None
            is_first = False
                
            plot.plot(x[0], y[0], color='gray', linestyle='', marker='o', label=dot_lab)
            
        
fmod_for_session = lambda s: ForecastModifier(s)

def title_for_session(sess):
    s = sess_data.loc[sess]
    return f"Mean Forecasts {s.sess_date} (N={s.n}; Float={s.flt})"

#Plot Sessions
sp = SessionPlotter(group_data, mod_cb=fmod_for_session, title_cb=title_for_session)
sp.plot_sessions()
sp.save_figures(IMG_DIR, 'forecast')
