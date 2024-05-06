import pandas as pd
import matplotlib.pyplot as plt

print("## Generating Basic Session Plots")

INPUT_DIR = 'Analysis/input'
IMG_DIR = 'Analysis/temp/img'


group_data = pd.read_csv(f'{INPUT_DIR}/group.csv')
player_data = pd.read_csv(f'{INPUT_DIR}/player.csv')
sess_data = pd.read_csv(f'{INPUT_DIR}/session.csv').set_index('session')

TOB = (3, 1)
LABEL_SIZE = 16
SESSION_FIG_SIZE = (10, 6)

def plot_session(session, price, volume, shares, figsize=SESSION_FIG_SIZE):
    
    rounds = price.index.values
    
    plt.figure(figsize=figsize).set_facecolor('white')
    plot_1 = plt.subplot2grid(TOB, (0, 0))
    plot_2 = plt.subplot2grid(TOB, (1, 0), sharex=plot_1)
    plot_3 = plt.subplot2grid(TOB, (2, 0), sharex=plot_1)
    
    # Price Plot
    plot_1.plot(rounds, price, zorder=3)
    plot_1.set_ylabel('Price', fontsize=LABEL_SIZE)
    plot_1.get_xaxis().set_visible(False)
    
    #Volume Plot
    plot_2.bar( rounds, volume)
    plot_2.set_ylabel('Volume', fontsize=LABEL_SIZE)
    plot_2.get_xaxis().set_visible(False)

    
    #Share Paths
    part_codes = set(shares.index.get_level_values(0))
    for code in part_codes:
        plot_3.plot(shares.loc[code], color='lightgray')
    plot_3.set_ylabel('Shares', fontsize=LABEL_SIZE)
    plot_3.set_xlabel('Round', fontsize=LABEL_SIZE)
   
 
    plt.suptitle(f"{session.label}   (N = {session.n})"  , fontsize=22)

    plt.savefig(f'{IMG_DIR}/market_graph_{session.name}png', transparent=False)
    plt.close()
     
    
    
sessions = group_data.session.unique()

for sess in sessions:
    group_data_for_session = group_data[group_data.session == sess].set_index('round')
    player_data_for_session = player_data[player_data.session == sess].set_index('round')
    sess_d = sess_data.loc[sess]
    share_paths = player_data_for_session.groupby(['part_label', 'round']).shares.max()
    
    plot_session(sess_d, group_data_for_session.price, group_data_for_session.volume, share_paths)
