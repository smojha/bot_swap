import pandas as pd
import sys
if 'Preproc/code' not in sys.path:
    sys.path.insert(0, 'Preproc/code')
from Preproc.code.MarketPrice_MP import run_markets

def mp_task_gen(_df, gd):
    """
    Return a generator used to feed the multiprocessing task queue.
    Break up the given data frame by session and round and yield each group of data
    along with the previous price.
    """
    for sess, r in gd.index.values:
        ord_sr = _df.loc[(sess, r)]
        prev_price = gd.loc[(sess, r)].prev_price

        yield (sess, r), ord_sr, prev_price


def get_regular_market_data(od, gd):
    return mp_task_gen(od, gd)


def get_indiv_pi_data(od, gd, otype='ALL'):
    sp_list = od.reset_index().set_index(['session', 'participant', 'round']).index.unique().values

    for s, p, r in sp_list:
        if otype=='ALL':
            pi_data = od[~(od.participant == p) ].loc[(s,r)]
        else:
            pi_data = od[~(od.participant == p) | ~(od.type==otype)].loc[(s,r)]

        prev_price = gd.loc[(s, r)].prev_price
        yield (s, p, r), pi_data, prev_price

def get_indiv_pi_data_sell(od, gd):
    return get_indiv_pi_data(od, gd, otype='SELL')

def get_indiv_pi_data_buy(od, gd):
    return get_indiv_pi_data(od, gd, otype='BUY')


def get_order_pi_data(od, gd):
    sp_list = od.reset_index().set_index(['session', 'round', 'uid']).index.unique().values

    for s,r,u in sp_list:
        sr_data = od.loc[(s,r)]
        pi_data = sr_data[~(sr_data.uid == u)]
        prev_price = gd.loc[(s,r)].prev_price
        yield (s,r,u), pi_data, prev_price


def as_frame(d, suffix='', idx=['session', 'round']):
    s = f'_{suffix}' if suffix else ''
    cols = idx + [f'price{s}', f'volume{s}']
    return  pd.DataFrame(d, columns=cols).set_index(idx)

def get_market_results(title, f, suffix, idx=['session', 'round']):
    print("Running Counterfactuals:", title)
    res = run_markets(f(order_data, group_data))
    return as_frame(res, suffix=suffix, idx=idx)

def get_market_results_pi(title, f, suffix):
    return get_market_results(title, f, suffix, idx=['session', 'participant', 'round'])

def join_all_dfs(_dfs):
    """
    Join a list of DataFrames on index.
    """
    all_cf = None
    for df in _dfs:
        if all_cf is None:
            all_cf = df
            continue
        all_cf = all_cf.join(df)
    all_cf.sort_index(inplace=True)
    return all_cf

if __name__ == '__main__':
    from MarketPrice_MP import run_markets

    order_data = pd.read_csv('Preproc/temp/preproc_orders.csv').set_index(['session', 'round'])
    group_data = pd.read_csv('Preproc/temp/preproc_group.csv').set_index(['session', 'round'])

    #Make the round 1 prev_prices = 14.  This is the price that will appear if
    #no trades occur
    idx = pd.IndexSlice
    group_data.loc[idx[:, 1], 'prev_price'] = 14


    # Define the jobs to do in (<label>, <generator function>, <suffix>) tuples
    print("#####  Order Type PI")
    jobs = [
        ('True Markets', get_regular_market_data, ''),
    ]
    dfs = [get_market_results(*j) for j in jobs]
    all_cf = join_all_dfs(dfs)
    boog = join_all_dfs(dfs)

    print("#####  Individual Participant PI")
    jobs = [
        ('Individual Price Impact - ALL', get_indiv_pi_data, 'pi_all'),
        ('Individual Price Impact - No SELL', get_indiv_pi_data_sell, 'pi_sell'),
        ('Individual Price Impact - No BUY', get_indiv_pi_data_buy, 'pi_buy'),
    ]
    dfs = [get_market_results_pi(*j) for j in jobs]
    all_cf = join_all_dfs(dfs)
    all_cf.to_csv('Preproc/temp/preproc_price_impacts.csv')

    print("#####  Individual Order PI")
    df = get_market_results('Individual Order', get_order_pi_data, 'pi_order', idx=['session', 'round', 'uid'])
    df.to_csv('Preproc/temp/preproc_order_price_impact.csv')
