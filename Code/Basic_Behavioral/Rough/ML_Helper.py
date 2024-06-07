import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob
from sklearn.svm import LinearSVC

def basic_price_data(order_data):
    sell_orders = []
    min_sell_price = []
    buy_orders = []
    max_buy_price = []
    market_price = []
    volume = []
    for round in np.unique(order_data['round_number']):
        df = order_data[order_data['round_number']== round]
        sell_orders.append(np.sum(df[df['type'] == 'SELL']['quantity']))
        min_sell_price.append(np.min(df[df['type'] == 'SELL']['price']))
        buy_orders.append(np.sum(df[df['type'] == 'BUY']['quantity']))
        max_buy_price.append(np.max(df[df['type'] == 'BUY']['price']))
        market_price.append(np.unique(df['market_price']))
        volume.append(np.unique(df['volume']))


    #turning into numpy arrays cause its nice
    sell_orders_array = np.array(sell_orders)
    min_sell_price_array = np.array(min_sell_price)
    buy_orders_array = np.array(buy_orders)
    max_buy_price_array = np.array(max_buy_price)
    market_price_array = np.array(market_price)
    volume_array = np.array(volume)
    return sell_orders_array, min_sell_price_array, buy_orders_array, max_buy_price_array,market_price_array, volume_array

def get_round_risk_adjusted(round_data):
    risk_adjusted_score=[]
    for i in np.unique(round_data['subsession.round_number']):
        if i <= 3:
            risk_adjusted_score.append(None)
        else:
            r1 = round_data[round_data['subsession.round_number'] == i]
            risk_adjusted_score.append(np.mean(r1["player.dose_r"]))
    return risk_adjusted_score
risk_adjusted_score = get_round_risk_adjusted(round_data)

def get_risk_adj_mv_avg(round_data, m):
    risk_adjusted_score = get_round_risk_adjusted(round_data)
    mv_avg = []
    for idx, score in enumerate(risk_adjusted_score):
        if idx < 3: # makes sure not in practice
            continue
        else:
            scores = []
            if idx - m < 3: # if moving average would go into practice then cut avg short
                if idx - 3 == 0: #fixes 0 case
                    scores.append(risk_adjusted_score[idx])
                else:
                    for i in range(idx - 3):
                        scores.append(risk_adjusted_score[idx - i])
            else:
                for i in range(idx - m):
                    scores.append(risk_adjusted_score[idx - i])
            mv_avg.append(np.mean(scores))
    return mv_avg

def get_forecast_data(round_data):
    f1mean_forecast=[]
    f2mean_forecast=[]
    f3mean_forecast=[]
    f4mean_forecast=[]
    for i in np.unique(round_data['subsession.round_number']):
        r1 = round_data[round_data['subsession.round_number'] == i]
        f1mean_forecast.append(np.mean(r1['player.f0']))
        f2mean_forecast.append(np.mean(r1['player.f1']))
        f3mean_forecast.append(np.mean(r1['player.f2']))
        f4mean_forecast.append(np.mean(r1['player.f3']))
    return [f1mean_forecast, f2mean_forecast, f3mean_forecast, f4mean_forecast]

def forecast_error(round_data,market_price_array, t, m):
    forecasts = get_forecast_data(round_data)
    if m == 1:
        forecast_array = forecasts[0]
    elif m == 3:
        forecast_array = forecasts[1]
    elif m == 6:
        forecast_array = forecasts[2]
    elif m == 11:
        forecast_array = forecasts[3]

    forecast_error = forecast_array[t-m] - market_price_array[t]
    return forecast_error[0]

def generate_forecast_error(round_data, market_price_array, m):
    forecast_error_array = []
    for t, price in enumerate(market_price_array):
        if t < m:
            error = None
        else:
            error = forecast_error(round_data, market_price_array, t, m)
        forecast_error_array.append(error)
    return forecast_error_array

def get_orderbook_pressure_per_round(order_data, t):
    round_data = order_data[order_data['round_number']== t]
    market_price = np.unique(round_data['market_price'])[0]

    buy_d = round_data[round_data['type'] =='BUY']
    max_unfilled_bid = np.max(buy_d[buy_d['price'] <market_price]['price'])
    bid_quantity = np.sum(buy_d[buy_d['price'] ==max_unfilled_bid]['quantity'])

    ask_d = round_data[round_data['type'] =='SELL']
    min_unfilled_ask = np.min(ask_d[ask_d['price'] > market_price]['price'])
    ask_quantity = np.sum(ask_d[ask_d['price'] ==min_unfilled_ask]['quantity'])

    obook_pressure = (max_unfilled_bid * bid_quantity + min_unfilled_ask * ask_quantity)/(bid_quantity+ask_quantity)
    return obook_pressure

def get_order_book_ressure(order_data ):
    order_book_pressure = []
    for round in np.unique(order_data['round_number']):
        order_book_pressure.append(get_orderbook_pressure_per_round(order_data, round))
    return (order_book_pressure)

def get_asset_allocation(round_data, market_price_array):
    allocation_list = []
    for i in np.unique(round_data['subsession.round_number']):
        r1 = round_data[round_data['subsession.round_number'] == i]
        cash = np.sum(r1['player.cash'])
        shares = np.sum(r1['player.shares'])
        if i == 4:
            price = 14
        else:
            price = market_price_array[i-2] # -1 since idx starts at 1, -1 for lag
        market_cap = shares * price
        allocation = cash.item() / market_cap.item()
        allocation_list.append(allocation)
    return allocation_list

def organize_dataorder_data(order_data, market_price_array, risk_adjusted_score, order_book_pressure, allocation_list):
    round_ml_data = {
    'price': [],
    'volume': [],
    'lag_price': [],
    'lag_volume': [],
    'price_change': [],
    'period-1 forecast error': [],
    'period-3 forecast error': [],
    'period-6 forecast error': [],
    'period-11 forecast error': [],
    'laged_risk_parameter_mv_avg': [],
    'rounds_remaining': [],
    'order_book_pressure': [],
    'asset_allocation': []
}

    # Populate the lists with values for each round
    for round in np.unique(order_data['round_number']):
        if round > 3:
            round_ml_data['price'].append(market_price_array[round-1][0])
            round_ml_data['volume'].append(market_price_array[round-1][0])
            if round == 4:
                round_ml_data['price_change'].append(market_price_array[round-1][0] - 14)
                round_ml_data['lag_price'].append(14)
                round_ml_data['lag_volume'].append(None)
                round_ml_data[f'laged_risk_parameter_mv_avg'].append(None)
            else:
                round_ml_data['price_change'].append(market_price_array[round-1][0] - market_price_array[round-2][0])
                round_ml_data['lag_price'].append(market_price_array[round-2][0])
                round_ml_data['lag_volume'].append(market_price_array[round-2][0])
                round_ml_data[f'laged_risk_parameter_mv_avg'].append(risk_adjusted_score[round - 3 - 2]) # -3 since it doesn't include practice, -1 since round index starts at 1, -1 for lagged
            round_ml_data['rounds_remaining'].append(33 - round)
            round_ml_data['order_book_pressure'].append(order_book_pressure[round-1])
            round_ml_data['asset_allocation'].append(allocation_list[round-1])

    for m in [1,3,6,11]:
        round_ml_data[f'period-{m} forecast error'] = generate_forecast_error(round_data, market_price_array[3:], m)
    round_ml_data_df = pd.DataFrame.from_dict(round_ml_data)
    return round_ml_data_df
