#! /bin/bash

echo "###"
echo "###"
echo "### Analyzing"
echo "###"

# ensure that the temp and output directories exist and are empty
[ -d Analysis/temp ] || mkdir Analysis/temp
rm -rf Analysis/temp/*

[ -d Analysis/temp/img ] || mkdir Analysis/temp/img
rm -f Analysis/temp/img/*

[ -d Analysis/temp/tex ] || mkdir Analysis/temp/tex
rm -f Analysis/temp/tex/*


[ -d Analysis/output ] || mkdir Analysis/output
rm -f Analysis/output/*

#export PYTHONPATH='Analysis/code'

# Copy 
[ -d Analysis/input ] || mkdir Analysis/input
rm -f Analysis/input/*
cp Preproc/output/* Analysis/input/

# run the prepoc code
python Analysis/code/market_charts.py
python Analysis/code/forecast_plots.py
python Analysis/code/indiv_orders.py
python Analysis/code/demographic_table.py


# copy files to output
cp -R Analysis/temp/* Analysis/output
#rm -f temp/*
