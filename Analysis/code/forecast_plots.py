import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

print("## Generating Forecast Plots")

if 'Analysis/code' not in sys.path:
    sys.path.insert(0, 'Analysis/code')
   
from SessionPlotter import SessionPlotter, SessionPlotModifier



INPUT_DIR = 'Analysis/input'
TEMP_DIR = 'Analysis/temp'


group_data = pd.read_csv(f'{INPUT_DIR}/group.csv')
player_data = pd.read_csv(f'{INPUT_DIR}/player.csv')
sess_data = pd.read_csv(f'{INPUT_DIR}/session.csv').set_index('session')


## Consolidate Forecast Data
p_grp = player_data.groupby(['session', 'round'])
f_means = p_grp[['f0', 'f1', 'f2', 'f3']].mean()
t_rnd = p_grp[['fcast_rnd_0', 'fcast_rnd_1', 'fcast_rnd_2', 'fcast_rnd_3']].max()

forecast = f_means.join(t_rnd)


#Callback to get session modifier
class ForecastModifier(SessionPlotModifier):
    def __init__(self, session):
        self.session = session
        
    def modify(self, plot):
        f_data = forecast.loc[self.session]
        is_first = True
        for _, row in f_data.iterrows():
            y = [ row.f0, row.f1, row.f2, row.f3 ]
            x = [ row.fcast_rnd_0, row.fcast_rnd_1, row.fcast_rnd_2, row.fcast_rnd_3 ]
            plot.plot(x, y, color='gray', label=None)
            
            lab = "Current period forecast" if is_first else None
            is_first = False
                
            plot.plot(x[0], y[0], color='gray', marker='o', label=lab)
            
        
fmod_for_session = lambda s: ForecastModifier(s)

def title_for_session(sess):
    s = sess_data.loc[sess]
    return f"Mean Forecasts {s.label} (N={s.n}; Float={s.flt})"

#Plot Sessions
sp = SessionPlotter(group_data, mod_cb=fmod_for_session, title_cb=title_for_session)
sp.plot_sessions()
sp.save_figures(TEMP_DIR, 'forecast')
