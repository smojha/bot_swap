import pandas as pd

DATA_DIR = 'Data/Surveys'
TEMP_DIR = 'Preproc/temp'

#
#  Load the survey data
pre_1 = pd.read_csv(f"{DATA_DIR}/Neurofinance 1st pre-experiment.csv")
pre_2 = pd.read_csv(f"{DATA_DIR}/Neurofinance 2nd pre-experiment.csv")
post = pd.read_csv(f"{DATA_DIR}/Neurofinance post-experiment.csv")

#
# For now, these seem to be the columns for the participant labels, for now
pre_1_idx = "Print Prolific ID (as substitute for Name)"
pre_2_idx = "Please enter your Prolific ID"
post_idx = "Please enter your prolific ID:"
idx_cols = [pre_1_idx, pre_2_idx, post_idx]

#
# Rename if participant labels to something common (part_label)
f = lambda x:  'part_label' if x in idx_cols else x

pre_1 = pre_1.rename(mapper=f, axis=1).set_index('part_label')
pre_2 = pre_2.rename(mapper=f, axis=1).set_index('part_label')
post = post.rename(mapper=f, axis=1).set_index('part_label')

#
# Join the survey data frames together
all = pre_1.join(pre_2, lsuffix='pre_1', rsuffix='pre_2', how="outer").join(post, lsuffix='pre_2', rsuffix='post',  how="outer")

#
# Write out the results
all.to_csv(f"{TEMP_DIR}/all_surveys.csv")
