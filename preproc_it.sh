#! /bin/bash

echo "###"
echo "###"
echo "### Preprocessing"
echo "###"

# ensure that the temp and output directories exist and are empty
[ -d Preproc/temp ] || mkdir Preproc/temp
rm -fR Preproc/temp/*

[ -d Preproc/temp/payments ] || mkdir Preproc/temp/payments
rm -fR Preproc/temp/payments/*

[ -d Preproc/temp/bio ] || mkdir Preproc/temp/bio
rm -fR Preproc/temp/bio/*

# special directory to store biometric data
[ -d bio_repo ] || mkdir bio_repo
cp -R bio_repo/* Preproc/temp/bio

#if there are no panel data copied from the bio_repo, then ensure the panels directory
[ -d Preproc/temp/bio/panels ] || mkdir Preproc/temp/bio/panels
# It is usual to delete all files in the directory, but not here.  we need to pres

[ -d Preproc/output ] || mkdir Preproc/output
rm -fR Preproc/output/*




# run the prepoc code
python Preproc/code/normalize.py
python Preproc/code/preproc_surveys.py
python Preproc/code/preproc_session.py
python Preproc/code/preproc_player_group_orders.py
python Preproc/code/preproc_player.py

#python Preproc/code/preproc_counterfactuals.py
python Preproc/code/preproc_participant.py
python Preproc/code/preproc_page_time.py

# Biometric Preprocessing
python Preproc/code/add_time_to_bio.py
python Preproc/code/create_bio_panels.py

python Preproc/code/generate_prolific_bonus_payment_files.py
python Preproc/code/flatten_data.py

# copy files to output
base='preproc_'
for FILE in Preproc/temp/$base*
do
  name="$(basename $FILE)"
  output_name="${name/$base/}"
  cp $FILE Preproc/output/$output_name
done
cp -R Preproc/temp/payments Preproc/output/
cp -R Preproc/temp/bio Preproc/output
# Flattened data files don't go to github anymore
# cp Preproc/temp/flattened_data* Preproc/output
#rm -f temp/*


[ -d Preproc/data_preproc ] || mkdir Preproc/data_preproc
rm -fR data_preproc/*
cp -R Preproc/output/* data_preproc

#save the bio data out to the bio_repo to save time next time
rm -fR bio_repo/*
cp -R Preproc/temp/bio/* bio_repo
