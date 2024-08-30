import pandas as pd

df = pd.read_csv('/Users/cadyngo/Desktop/participant.csv')

participants = df['part_label'].unique()

# filter for Prolific only
filtered_labels = [label for label in participants if len(label) == 24]

filtered_labels_list = list(filtered_labels)
print(", ".join(filtered_labels_list))