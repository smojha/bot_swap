import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob
from sklearn.svm import LinearSVC

def get_negative_inflection(buy_orders, sell_orders, session, hide_graph = "no"):
    buy_sell_diff = []
    for round,ask_count in enumerate(sell_orders):
        bid_count = buy_orders[round]
        if (ask_count > bid_count) and not (sell_orders[round-1] > buy_orders[round-1]):
            buy_sell_diff.append(1)
        else:
            buy_sell_diff.append(0)
    np.array(buy_sell_diff)

    if hide_graph == "yes":
        plt.plot(buy_sell_diff)
        plt.title(f"{session} Bid_Ask Change")
    
    return buy_sell_diff

def price_change(idx, market_price_array):
    if idx == 0:
        prev = 0
    else:
        prev = market_price_array[idx-1]
    return market_price_array[idx] - prev

def get_lag_price(market_price_array, hide_graph = "no"):
    lag_price = []
    for round,price in enumerate(market_price_array):
        lag_price.append(price_change(round, market_price_array))
    
    if hide_graph == "yes":
        plt.plot(lag_price)
        plt.hlines(0, xmin=0, xmax=len(lag_price)-1, colors='r', linestyles='dashed')
        plt.xlabel('Round')
        plt.ylabel('Price Change')
        plt.title('Lagged Price Changes')
        plt.show()
    return lag_price


def period_mv_avg(idx, market_price_array, period, include_beg="no"):
    if idx < period:
        if include_beg == 'yes':
            mv_avg = np.mean(market_price_array[:idx])
        else:
            mv_avg = 14
    else:
        mv_avg = np.mean(market_price_array[idx-period:idx])

    return mv_avg

def get_moving_average(market_price_array, period, include_beg="no",hide_graph = 'no'):
    if include_beg == 'yes':
        print(f""" Note: You are including in the moving average periods that do not have {period} rounds of previous data. 
        The means for those periods will be a simple average of the periods up until this point from index 0. 
        If you want to exclude then the include_beg parameter should be set to no.""")
    
    mv_avg = []
    lag_price = get_lag_price(market_price_array)
    for round, price in enumerate(market_price_array):
        mv_avg.append(period_mv_avg(round, market_price_array, 3, include_beg= include_beg))
    if hide_graph == "yes":
        plt.plot(mv_avg)
        plt.hlines(14, xmin=0, xmax=len(lag_price)-1, colors='r', linestyles='dashed')
        plt.xlabel('Round')
        plt.ylabel("Price")
        plt.title(f'{period} Price moving averge')
        plt.show()
    return lag_price


def get_forecast_data(round_data):
    f1mean_forecast=[]
    f2mean_forecast=[]
    f3mean_forecast=[]
    f4mean_forecast=[]
    for i in np.unique(round_data['subsession.round_number']):
        if i > 3:
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
    return forecast_error

def generate_forecast_error(round_data, market_price_array, m):
    forecast_error_array = []
    for t, price in enumerate(market_price_array):
        if t < m:
            error = None
        else:
            error = forecast_error(round_data, market_price_array, t, m)
        forecast_error_array.append(error)
    return forecast_error_array

def lag_volume(buy_orders, sell_orders, t):
    volume = np.add(buy_orders, sell_orders)
    if t < 1:
        lag_volume = None
    else:
        lag_volume= volume[t-1]
    return lag_volume

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

def get_asset_allocation(round_data, t):
    if t < 1:
        price = 14
    else:
        price = np.unique(round_data[round_data['subsession.round_number']== 4]['group.price'])[0]
    player_cash = np.sum(round_data[round_data['subsession.round_number']== t]['player.cash'])
    stock_value = np.sum(round_data['player.shares'])* price
    return player_cash/stock_value