#! /bin/bash

echo "###"
echo "###"
echo "### Preprocessing"
echo "###"

# ensure that the temp and output directories exist and are empty
[ -d Preproc/temp ] || mkdir Preproc/temp
rm -f Preproc/temp/*
[ -d Preproc/output ] || mkdir Preproc/output
rm -f Preproc/output/*



# run the prepoc code
python Preproc/code/normalize.py
python Preproc/code/preproc_surveys.py
python Preproc/code/preproc_player_group_orders.py

#python Preproc/code/preproc_counterfactuals.py
python Preproc/code/preproc_participant.py
python Preproc/code/preproc_page_time.py



# copy files to output
base='preproc_'
for FILE in Preproc/temp/$base*
do
  name="$(basename $FILE)"
  output_name="${name/$base/}"
  cp $FILE Preproc/output/$output_name
done
#rm -f temp/*

