import pandas as pd

print("###\n###\n### Flattening Data")

BIO_PAGE_TEMP_DIR = 'Preproc/temp/bio/page_merge'
BIO_TEMP_PANELS_DIR = 'Preproc/temp/bio/panels'
TEMP_DIR = 'Preproc/temp'

#Read in experiment data
sess_data = pd.read_csv(f"{TEMP_DIR}/preproc_session.csv").set_index('session')
group_data = pd.read_csv(f"{TEMP_DIR}/preproc_group.csv").set_index(['session', 'round'])
part_data = pd.read_csv(f"{TEMP_DIR}/preproc_participant.csv").set_index(['session'])
player_data = pd.read_csv(f"{TEMP_DIR}/preproc_player.csv").set_index(['part_label', 'round'])


# Clean out some columns that will be duplicated in the join
player_columns = list(player_data)
for c in ['session']:
    player_columns.remove(c)
player_data = player_data[player_columns]

## Joining exp data
a = group_data.join(sess_data, on='session')
a = a.join(part_data, on='session')
flat = a.join(player_data[player_columns], on=['part_label', 'round'])


## Read in bio data
bio_bvp = pd.read_csv(f"{BIO_TEMP_PANELS_DIR}/bio_panel_BVP.csv").set_index(['page', 'part_label', 'round', 'analysis_type'])
bio_eda = pd.read_csv(f"{BIO_TEMP_PANELS_DIR}/bio_panel_EDA.csv").set_index(['page', 'part_label', 'round', 'analysis_type'])
bio_hr = pd.read_csv(f"{BIO_TEMP_PANELS_DIR}/bio_panel_HR.csv").set_index(['page', 'part_label', 'round', 'analysis_type'])
bio_temp = pd.read_csv(f"{BIO_TEMP_PANELS_DIR}/bio_panel_TEMP.csv").set_index(['page', 'part_label', 'round', 'analysis_type'])

# Rename bio columns
bio_bvp.rename(mapper=lambda x: 'bvp_'+x, axis='columns', inplace=True)
bio_eda.rename(mapper=lambda x: 'eda_'+x, axis='columns', inplace=True)
bio_hr.rename(mapper=lambda x: 'hr_'+x, axis='columns', inplace=True)
bio_temp.rename(mapper=lambda x: 'temp_'+x, axis='columns', inplace=True)

# join all bio data
all_bio = bio_eda.join(bio_bvp).join(bio_hr).join(bio_temp)

#filter out non-bio participants from the flat
bio_parts = all_bio.index.levels[1]
bio_flat = flat.reset_index().set_index('part_label').loc[bio_parts]

#join bio data to flat data
all_bio.reset_index(level=['page', 'analysis_type'], inplace=True)
bio_flat = bio_flat.reset_index().set_index(['part_label', 'round'])
flat_w_bio = bio_flat.join(all_bio)
flat_w_bio = flat_w_bio.reset_index().sort_values(['label', 'part_label', 'page', 'analysis_type', 'round'])


#write to disk
flat.to_csv(f"{TEMP_DIR}/flattened_data.csv")
flat_w_bio.to_csv(f"{TEMP_DIR}/flattened_data_w_bio.csv")
