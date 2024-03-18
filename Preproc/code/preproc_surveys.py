import pandas as pd

DATA_DIR = 'Data'
TEMP_DIR = 'preproc/temp'


def join_surveys():
    print("# Joining Surveys")
    #
    #  Load the survey data
    pre_1 = pd.read_csv(f"{DATA_DIR}/Surveys/Neurofinance 1st pre-experiment.csv")
    pre_2 = pd.read_csv(f"{DATA_DIR}/Surveys/Neurofinance 2nd pre-experiment.csv")
    post = pd.read_csv(f"{DATA_DIR}/Surveys/Neurofinance post-experiment.csv")
    
    #
    # For now, these seem to be the columns for the participant labels, for now
    pre_1_idx = "Print Prolific ID (as substitute for Name)"
    pre_2_idx = "Please enter your Prolific ID"
    post_idx = "Please enter your prolific ID:"
    idx_cols = [pre_1_idx, pre_2_idx, post_idx]
    
    #
    # Rename if participant labels to something common (part_label)
    f = lambda x:  'part_label' if x in idx_cols else x
    
    pre_1.rename(mapper=f, axis=1, inplace=True)
    pre_2.rename(mapper=f, axis=1, inplace=True)
    post.rename(mapper=f, axis=1, inplace=True)
    
    #
    #  Somehow, we are getting duplicate submissions.  Remove the duplicates
    pre_1.drop_duplicates(subset='part_label', inplace=True)
    pre_2.drop_duplicates(subset='part_label', inplace=True)
    post.drop_duplicates(subset='part_label', inplace=True)

    
    pre_1 = pre_1.set_index('part_label')
    pre_2 = pre_2.set_index('part_label')
    post = post.set_index('part_label')
    
    #
    # Join the survey data frames together
    all = pre_1.join(pre_2, lsuffix='_pre_1', rsuffix='_pre_2', how="outer").join(post, lsuffix='_pre_2', rsuffix='_post',  how="outer")
    return all

#Rename columns to something sane
def rename_columns(df):
    print ("# Renaming Columns")
    mapper = {
        'Given the exclusion criteria, please confirm that you qualify to participate in the experiment:': 'confirm',
        'Please initial one option below to indicate whether or not you consent to us contacting you in the future:':'future_contact',
        "Print Participant's Initials (as substitute for signature)": 'signature',
     'Please indicate your consent:': 'consent',
     'Your age (in years):': 'age',
     'Your gender:': 'gender',
     'Are you of Hispanic, Latino/a, or of Spanish origin? (one or more categories may be selected)': 'hisp',
     'What is your race?': 'race',
     'Studies background': 'major',
     'Are you a native English speaker (i.e. is English your mother tongue?)': 'native_eng',
     'On a scale from 0 to 5, how good is your knowledge of English? (If YES to previous question, please mark 5 here)': 'proficient',
     'Are you currently under medication treatment for depression, anxiety, or other psychiatric or neurological conditions?': 'psych_cond',
     'How would you rate your risk-taking behavior in general, on a scale from 1-7._pre_2': 'risk_gen',
     'How would you rate your financial risk-taking behavior, on a scale from 1-7._pre_2': 'risk_fin',
     'You have been given $100. You can invest any part of this money in a risky asset. If the investment is successful, the risky asset returns 2.5 times the amount invested with a probability of one-half and nothing with a probability of one-half. You can also choose not to invest at all, in which case you will keep the money you have. How much would you like to invest? (write amount in dollars)_pre_2': 'invest_100_pre',
     
     'During order entry you want to input a BUY order at price of 8.52 and a SELL order at a price of 7.89. What will happen to your orders for that period?': 'quiz_1',
     'During order entry the highest price at which you submit a BUY order is 16.78 and the lowest price at which others SELL is 17.22. The market price is 16.56 for that period. You will:': 'quiz_2',
     'You have 200 units of CASH at the start of a trading period and no STOCK. You do not trade that period. How much CASH do you have at the beginning of the next period?': 'quiz_3',
     'Your account has 5 STOCK and 100 CASH at the start of a trading period, and you do not BUY or SELL during that period. The dividend for that round is 1.00. How much CASH do you have at the start of the next round?': 'quiz_4',
     'After the final trading period, you have 4 remaining units of STOCK. The market price in the final period is 29. How many units of experiment CASH do you receive in exchange for your STOCK?': 'quiz_5',
     
     'Please enter the 3-digit ID. If you do not have it, enter the Prolific ID. ': '3dig_id',
     'Have you participated in similar trading experiments before?': 'similar',
     'On a scale from 1-10, how well did you understood the task and were able to trade as required?': 'understood',
     'Did you understand exactly what you had to do from the beginning?': 'understood_begin',
     'Did you follow any strategy when trading? Please describe, be as detailed as possible': 'strategy',
     'Do you have any suggestions to improve the experiment? i.e. the software, the trading instructions, time to enter orders, time to enter forecast, time to do the risk elicitation task etc. ': 'improve',
     'Do you own/trade stocks? ': 'own_stock',
     'Imagine you performed the tasks with another 99 persons. In terms of performance, on what place do you think you placed? How would you rate your outcome from 1-100?': 'self_place',
     'How would you rate your risk-taking behavior in general, on a scale from 1-7._post': 'risk_gen_post',
     'How would you rate your financial risk-taking behavior, on a scale from 1-7._post': 'rist_gen_pre',
     'You have been given $100. You can invest any part of this money in a risky asset. If the investment is successful, the risky asset returns 2.5 times the amount invested with a probability of one-half and nothing with a probability of one-half. You can also choose not to invest at all, in which case you will keep the money you have. How much would you like to invest? (write amount in dollars)_post': 'invest_100_post',
     'Choose what you prefer:': 'hl_01',
     'Choose what you prefer:.1': 'hl_02',
     'Choose what you prefer:.2': 'hl_03',
     'Choose what you prefer:.3': 'hl_04',
     'Choose what you prefer:.4': 'hl_05',
     'Choose what you prefer:.5': 'hl_06',
     'Choose what you prefer:.6': 'hl_07',
     'Choose what you prefer:.7': 'hl_08',
     'Choose what you prefer:.8': 'hl_09',
     'Choose what you prefer:.9': 'hl_10',
     'Choose what you prefer:.10': 'hl_11',
     'Choose what you prefer:.11': 'hl_12',
     }
    
    return df.rename(mapper=mapper, axis=1)


def fix_number_cols(df):
    print("# Fix number columns")
    df['invest_100_post'] = df.invest_100_post.str.extract(r'(\d+)').astype(float)
    df['inv_pre_num'] = df.invest_100_pre.str.extract(r'(\d+)').astype(float)

    df['age'] = df.age.str.extract(r'(\d+)').astype(float)
    
    return df


#Remove the Timestamp and Unnamed columns
def remove_unneeded(df):
    print ("# Removing uneeded survey columns")
    drop = []
    for c in list(df):
        if c.startswith("Unnamed") or c.startswith('Timestamp'):
            drop.append(c)
            
    ret = df.drop(drop, axis='columns')
    return ret


if __name__ == '__main__':
    all = join_surveys()
    all = rename_columns(all)
    all = remove_unneeded(all)
    all = fix_number_cols(all)
    
    #
    # Write out the results
    all.to_csv(f"{TEMP_DIR}/temp_surveys.csv")