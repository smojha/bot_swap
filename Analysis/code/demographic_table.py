import pandas as pd

INPUT_DIR = "Analysis/input"
TEX_DIR = "Analysis/temp/tex"

part_data = pd.read_csv(f"{INPUT_DIR}/participant.csv")
sess_data = pd.read_csv(f"{INPUT_DIR}/session.csv").set_index('session')
part_data = pd.read_csv(f"{INPUT_DIR}/participant.csv").set_index(['session', 'part_label'])


def get_sess_stats(r):
    df = r[['n', 'flt', 'rad', 'bias', 'disp', 'pa', 'dur', 'peak_price', 'peak_round']]
    
    df.loc[['rad', 'bias']] = df.loc[['rad', 'bias']].map("{0:.2f}".format).astype(str)
    df.loc[['n', 'flt', 'disp', 'pa', 'dur', 'peak_price', 'peak_round']] = df.loc[['n', 'flt', 'disp', 'pa', 'dur', 'peak_price', 'peak_round']].astype(int).astype(str)
    df.index = ['N', 'Float',
                  'Relative Absolute Bias',
                  'Average Bias',
                  'Total Dispersion',
                  'Price Amplitude',
                  'Duration',
                  'Peak Price',
                  'Peak Round']
    return df.T


def get_count_stat(p, col, name, fmat='d'):
    
    lab = p[p.index.str.len() < 10]
    prolific = p[p.index.str.len() >= 10]

    c_all = p.groupby(col).age.count()
    c_all.name='All'
    c_lab = lab.groupby(col).age.count()
    c_lab.name='Lab'
    c_pro = prolific.groupby(col).age.count()
    c_pro.name='Prolific'
    
    stg_1 = pd.merge(c_all, c_lab, how='left', left_index=True, right_index=True)
    c = pd.merge(stg_1, c_pro, how='left', left_index=True, right_index=True)
    c.index = pd.MultiIndex.from_product([[name], c.index.values])
    
    
    return c

def get_mean_stat(p, col, name, fmat='.2f'):
    _all = format(p[col].mean(), fmat)
    lab = format(p[p.index.str.len() < 10][col].mean(), fmat)
    prolific = format(p[p.index.str.len() >= 10][col].mean(), fmat)

    df = pd.DataFrame([[_all, lab, prolific]], columns=['All', 'Lab', 'Prolific'])
    df.index = pd.MultiIndex.from_tuples([(name, '(mean)')])    
    
    return df
  
        


def get_part_stats(p):
    
    mean_vars = [('age', 'Age'),
                 ('quiz_grade', 'Quiz Grade'),
                 ('market_bonus', 'Market Bonus'),
                 ('forecast_bonus', 'Forecast Bonus'),
                 ('risk_bonus', 'Risk Bonus'),
                 ('total_bonus', 'Total Bonus'),
                 ('rist_gen_pre', 'Risk Gen (pre)'),
                 ('risk_gen_post', 'Risk Gen (post)'),
                 ('invest_100_pre', 'Risk Finance (pre)'),
                 ('invest_100_post', 'Risk Finance (post)'),
                 ]
    
    _all = format(p.shape[0], 'd')
    lab = format(p[p.index.str.len() < 10].shape[0], 'd')
    prolific = format(p[p.index.str.len() >= 10].shape[0], 'd')

    n = pd.DataFrame([[_all, lab, prolific]], columns=['All', 'Lab', 'Prolific'])
    n.index = pd.MultiIndex.from_tuples([('N', ' ')])    
    
    
    rows = [n]
    for c, name in mean_vars:
        rows.append(get_mean_stat(p, c, name))
        
    df = pd.concat(rows)
    
    race_count = get_count_stat(p, 'race', 'Race')
    df = pd.concat([df, race_count])

    return df.fillna(0)
    

    
for sess, row in sess_data.iterrows():
    
    # Session Stats (includeing bubble metrics)
    s_stats = get_sess_stats(row)
    s_stats.to_latex(f'{TEX_DIR}/stats_sess_{sess}.tex')
    
    # Participant Stats
    parts = part_data.loc[sess]
    p_stats = get_part_stats(parts)
    p_stats.to_latex(f'{TEX_DIR}/stats_part_{sess}.tex')


    