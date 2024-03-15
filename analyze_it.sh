#! /bin/bash

echo "###"
echo "###"
echo "### Analyzing"
echo "###"

# ensure that the temp and output directories exist and are empty
[ -d Analysis/temp ] || mkdir Analysis/temp
rm -f Analysis/temp/*
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


# copy files to output

#rm -f temp/*
