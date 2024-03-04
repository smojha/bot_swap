#%%
import pandas as pd

player_data = pd.read_csv('Preproc/temp/normalized_player.csv')
order_data = pd.read_csv('Preproc/temp/normalized_orders.csv')
group_data = pd.read_csv('Preproc/temp/normalized_group.csv')

print("Determine short selling and buybacks for counterfactuals")

## is margin violation
player_data['is_mv'] = player_data['periods_until_auto_buy'] != -99


# Generate a UID column for all orders
# this by resetting the index.  So far the index is just the integer row numbers
# Calling #reset_index() causes that to become a column which we rename to 'uid'
order_data = order_data.reset_index().rename(mapper={'index': 'uid'}, axis=1)


#%%
# is shorting
# encode order type as a boolean True:SELL; False:BUY
order_data['is_sell'] = (order_data.type == 'SELL')

print("Splitting orders into BUYS and SELLS and tally buy and sell quantities for each player-round")
# sell_quant is 0 for buy orders and the same as quantity for sell orders
order_data['sell_quant'] = order_data.is_sell * order_data.quantity
# buy_quant is 0 for sell orders and the same as quantity for buy orders
order_data['buy_quant'] = (1 - order_data.is_sell) * order_data.quantity

# For each participant and round, tally the buy and sell quantities.
buy_sell = order_data.groupby(['participant', 'round'])[['buy_quant', 'sell_quant']].sum()

# Join the buy / sell quantities to the player data.
# Player data is naturally organized by participant and round number
# ".join" is a left join by default, so missing values are set to "nan"
# Set "NaN"s to zero and recast to int.
print("Join buy / sell quantites to player data")
p_with_sell_q =  player_data.join(buy_sell, on=['participant', 'round'])
p_with_sell_q.sell_quant = p_with_sell_q.sell_quant.fillna(0).astype(int)
p_with_sell_q.buy_quant = p_with_sell_q.buy_quant.fillna(0).astype(int)


#%%
# Group Level items
# Previous Price - Lag of market price
# It is important to not here that "prev_price" is the market price that prevails at the start of the round
# "price" is the market price that is calculated based on the orders submitted during that round.
print("Lagging market prices")
prev_price = group_data.groupby('session').price.shift(1)
# Insert the lagged price into the data frame immediately after the market price.
group_data.insert(3, 'prev_price', prev_price)

start_price = group_data.set_index(['session', 'round']).prev_price
start_price.name = 'market_price'
start_price = start_price.fillna(14)  # this should be round one price, set to the fundamental value.
#%%

# Join that previous price (now "market_price") into the working player data.
df = p_with_sell_q.join(start_price, on=['session', 'round'])
# Adding equity and margin related variables (again this is the working version of the player data)
print("Equity calculations")
df['stock_value'] = df.shares * df.market_price
df['equity'] = df.shares * df.market_price + df.cash

#%%
# Write all out to the temp directory
print("Write to disk")
group_data.to_csv('Preproc/temp/preproc_group.csv', index=False)
df.to_csv('Preproc/temp/preproc_player.csv', index=False)
order_data.to_csv('Preproc/temp/preproc_orders.csv', index=False)