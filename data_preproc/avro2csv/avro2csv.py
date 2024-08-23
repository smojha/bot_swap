import os
import glob
import csv
from fastavro import reader

def avro_to_csv(avro_file_path, csv_file_path):
    with open(avro_file_path, 'rb') as avro_file:
        avro_reader = reader(avro_file)
        schema = avro_reader.schema
        fieldnames = [field['name'] for field in schema['fields']]
        
        with open(csv_file_path, 'w', newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()
            
            for record in avro_reader:
                csv_writer.writerow(record)

def convert_all_avro_in_folder(input_folder, output_folder):
    avro_files = glob.glob(os.path.join(input_folder, '*.avro'))
    
    for avro_file in avro_files:
        csv_file = os.path.join(output_folder, os.path.basename(avro_file).replace('.avro', '.csv'))
        avro_to_csv(avro_file, csv_file)
        print(f"Converted {avro_file} to {csv_file}")

input_folder = os.path.expanduser("/Users/cadyngo/Desktop/Empatica Raw/0719")
output_folder = os.path.expanduser("/Users/cadyngo/Desktop/Empatica Raw/0719NEW")

convert_all_avro_in_folder(input_folder, output_folder)
