#! /bin/bash

echo "###"
echo "###"
echo "### Preprocessing"
echo "###"

# ensure that the temp and output directories exist and are empty
[ -d Preproc/temp ] || mkdir Preproc/temp
rm -fR Preproc/temp/*

[ -d Preproc/output ] || mkdir Preproc/output
rm -fR Preproc/output/*


# run the prepoc code
python Preproc/code/normalize.py
python Preproc/code/preproc_session.py
python Preproc/code/preproc_player_group_orders.py
python Preproc/code/preproc_player.py
python Preproc/code/preproc_participant.py
python Preproc/code/flatten_data.py


# copy files to output
base='preproc_'
for FILE in Preproc/temp/$base*
do
  name="$(basename $FILE)"
  output_name="${name/$base/}"
  cp $FILE Preproc/output/$output_name
done
cp Preproc/temp/flattened_data.csv Preproc/output/


[ -d Preproc/data_preproc ] || mkdir Preproc/data_preproc
cp Preproc/temp/flattened_data.csv Preproc/output/
rm -fR data_preproc/*
cp -R Preproc/output/* data_preproc
