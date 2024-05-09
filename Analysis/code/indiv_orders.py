import pandas as pd
import matplotlib.pyplot as plt

INPUT_DIR = 'Analysis/input'
IMG_DIR = 'Analysis/temp/img'

order_data = pd.read_csv(f'{INPUT_DIR}/orders.csv')
group_data = pd.read_csv(f'{INPUT_DIR}/group.csv')
player_data = pd.read_csv(f'{INPUT_DIR}/player.csv')


#unique sessions
sess = group_data.session.unique()
for s in sess:

    o = order_data[order_data.session == s]
    g = group_data[group_data.session == s]
    p = player_data[player_data.session == s]
    
    
    last_rnd_buyer = o[(o['round'] == 30) & (o['type'] == 'BUY')].part_label.unique()
    
    
    for u in p.part_label.unique():
        fig, axs = plt.subplots(2,1)
        ax = g.set_index('round').price.plot(ax=axs[0], label="Market Price")
    
        ub = o[(o.part_label == u) & (o['type'] == 'BUY')]
        max_b = ub.price.max()
        ax.scatter(ub['round'], ub.price, marker='^', c='gray', label="Offer")
        
        us = o[(o.part_label == u) & (o['type'] == 'SELL')]
        max_s = us.price.max()
        ax.scatter(us['round'], us.price, marker='v', c='orange', label="Ask")
        
        max_price = max(max_b, max_s)
            
        #Market executions
        exe = o[(o.part_label == u) & (o.quantity_final > 0)]
        ax.vlines(exe['round'], 0, max_price, colors='lightgray', linestyle='dotted', zorder=0, label="Executed Trade")
        ax.legend()
    
    
        
        #Share paths
        shares = p[p.part_label==u]
        ax = shares.set_index('round').shares.plot(ax=axs[1], label="Stock Pos.")
        max_shares = shares.shares.max()
        ax.vlines(exe['round'], 0, max_shares, colors='lightgray', linestyle='dotted', zorder=0, label="Executed Trade")
        ax.legend()


        fig.suptitle(f'Participant {u}')
        fig.savefig(f'{IMG_DIR}/participant_orders_{s}_{u}')
        
        plt.close()
        
# sess_data = pd.read_csv(f'{INPUT_DIR}/session.csv').set_index('session')
       
# _ord = order_data.set_index(['session', 'round'])
# _grp = group_data.set_index(['session', 'round'])
# for s in sess:
#     o = _ord.loc[s]
#     buys = o[o['type'] == 'BUY']
#     sells = o[o['type'] == 'SELL']
    
#     buy_tot = buys.groupby('round').quantity.sum()
#     sell_tot = sells.groupby('round').quantity.sum()
    
#     fig, ax = plt.subplots()
    
#     buy_tot.plot(ax=ax, label="BUY")
#     sell_tot.plot(ax=ax, label="SELL")
    
#     g = _grp.loc[s].price.plot(ax=ax, label="Market Price")
    
#     ax.legend()
    
#     d = sess_data.loc[s].label
#     ax.set_title(f"{s} - {d}")
    
#     fig.savefig(f'{IMG_DIR}/demand_supply_{s}')
#     plt.close()
    
    
    
    