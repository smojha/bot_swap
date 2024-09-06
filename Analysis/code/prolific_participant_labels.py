# Pulls ALL participant labels from the participant.csv file

import pandas as pd

df1 = pd.read_csv('/Users/cadyngo/Desktop/participant.csv')

participants1 = df1['part_label'].unique()

# filter for Prolific only
filtered_labels = [label for label in participants1 if len(label) == 24]

filtered_labels_list = list(filtered_labels)
#print(", ".join(filtered_labels_list))


# Pulls participant labels from new experiments

df2 = pd.read_csv('/Users/cadyngo/Desktop/experiment1.csv')

participants2 = df2['Participant id'].unique()
print(", ".join(participants2))
