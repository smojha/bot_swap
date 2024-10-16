import pandas as pd

print ("## Generating Session Stats")

INPUT_DIR = "Analysis/input"
TEX_DIR = "Analysis/temp/tex"

sess_data = pd.read_csv(f"{INPUT_DIR}/session.csv").set_index('session')
sess_data = sess_data.dropna()
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
    
    lab = p[p.site == 'Lab']
    prolific = p[p.site=='Prolific']

    c_all = p.groupby(col).surv_age.count()
    c_all.name='All'
    c_lab = lab.groupby(col).surv_age.count()
    c_lab.name='Lab'
    c_pro = prolific.groupby(col).surv_age.count()
    c_pro.name='Prolific'
    
    stg_1 = pd.merge(c_all, c_lab, how='left', left_index=True, right_index=True)
    c = pd.merge(stg_1, c_pro, how='left', left_index=True, right_index=True)
    c.index = pd.MultiIndex.from_product([[name], c.index.values])
    
    
    return c

def get_mean_stat(p, col, name, fmat='.2f'):
    _all = format(p[col].mean(), fmat)
    lab = format(p[p.site == 'Lab'][col].mean(), fmat)
    prolific = format(p[p.site=='Prolific'][col].mean(), fmat)

    df = pd.DataFrame([[_all, lab, prolific]], columns=['All', 'Lab', 'Prolific'])
    df.index = pd.MultiIndex.from_tuples([(name, '(mean)')])    
    
    return df
  
MEAN_VARS = [
                  ('market_bonus', 'Market Bonus'),
                  ('forecast_bonus', 'Forecast Bonus'),
                  ('risk_bonus', 'Risk Bonus'),
                  ('total_bonus', 'Total Bonus'),
                  
                 ]       
#('surv_age', 'Age'),
# ('quiz_grade', 'Quiz Grade'),
# ('quiz_1_init_score', 'Quiz 1'),
# ('quiz_2_init_score', 'Quiz 2'),
# ('quiz_3_init_score', 'Quiz 3'),
# ('quiz_4_init_score', 'Quiz 4'),
# ('quiz_5_init_score', 'Quiz 5'),
# ('surv_risk_gen', 'Risk Gen (pre)'),
# ('surv_risk_gen_post', 'Risk Gen (post)'),
# ('surv_invest_100_pre', 'Invest 100 (pre)'),
# ('surv_invest_100_post', 'Invest 100 (post)'),

def get_part_stats(p, mean_vars):

    
    _all = format(p.shape[0], 'd')
    lab = format(p[p.site == 'Lab'].shape[0], 'd')
    prolific = format(p[p.site=='Prolific'].shape[0], 'd')

    n = pd.DataFrame([[_all, lab, prolific]], columns=['All', 'Lab', 'Prolific'])
    n.index = pd.MultiIndex.from_tuples([('N', ' ')])    
    
    
    rows = [n]
    for c, name in mean_vars:
        rows.append(get_mean_stat(p, c, name))
        
    df = pd.concat(rows)
    

    return df.fillna(0)
    

for sess, row in sess_data.iterrows():
    
    # Session Stats (includeing bubble metrics)
    s_stats = get_sess_stats(row)
    s_stats.to_latex(f'{TEX_DIR}/stats_sess_{sess}.tex')
    
    # Participant Stats
    parts = part_data.loc[sess]
    p_stats = get_part_stats(parts, MEAN_VARS)
    p_stats.to_latex(f'{TEX_DIR}/stats_part_{sess}.tex')


    


    
    
#Create stats table for all
MEAN_VARS_FULL_QUIZ = [
                  ('market_bonus', 'Market Bonus'),
                  ('forecast_bonus', 'Forecast Bonus'),
                  ('risk_bonus', 'Risk Bonus'),
                  ('total_bonus', 'Total Bonus'),
                 ]       
all_stats = get_part_stats(part_data.reset_index(level=0, drop=True), MEAN_VARS_FULL_QUIZ)
all_stats.style\
    .to_latex(f'{TEX_DIR}/stats_part_all.tex', hrules=True, multirow_align='t')