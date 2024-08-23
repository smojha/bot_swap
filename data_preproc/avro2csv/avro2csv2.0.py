import os
import glob
import json
import csv
from avro.datafile import DataFileReader
from avro.io import DatumReader

def process_avro_files(input_folder, output_folder):
    # check each output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # data containers
    accelerometer_data = []
    gyroscope_data = []
    eda_data = []
    temperature_data = []
    bvp_data = []
    systolic_peaks_data = []
    steps_data = []
    tags_data = []

    # process each avro file
    avro_files = glob.glob(os.path.join(input_folder, '*.avro'))
    for avro_file_path in avro_files:
        try:
            with open(avro_file_path, 'rb') as avro_file:
                reader = DataFileReader(avro_file, DatumReader())
                data = next(reader)

                # accelerometer
                acc = data["rawData"]["accelerometer"]
                acc_timestamp = [round(acc["timestampStart"] + i * (1e6 / acc["samplingFrequency"])) for i in range(len(acc["x"]))]
                delta_physical = acc["imuParams"]["physicalMax"] - acc["imuParams"]["physicalMin"]
                delta_digital = acc["imuParams"]["digitalMax"] - acc["imuParams"]["digitalMin"]
                acc_x_g = [val * delta_physical / delta_digital for val in acc["x"]]
                acc_y_g = [val * delta_physical / delta_digital for val in acc["y"]]
                acc_z_g = [val * delta_physical / delta_digital for val in acc["z"]]
                for i in range(len(acc_x_g)):
                    accelerometer_data.append([acc_timestamp[i], acc_x_g[i], acc_y_g[i], acc_z_g[i]])

                # gyroscope
                gyro = data["rawData"]["gyroscope"]
                gyro_timestamp = [round(gyro["timestampStart"] + i * (1e6 / gyro["samplingFrequency"])) for i in range(len(gyro["x"]))]
                for i in range(len(gyro["x"])):
                    gyroscope_data.append([gyro_timestamp[i], gyro["x"][i], gyro["y"][i], gyro["z"][i]])

                # eda
                eda = data["rawData"]["eda"]
                eda_timestamp = [round(eda["timestampStart"] + i * (1e6 / eda["samplingFrequency"])) for i in range(len(eda["values"]))]
                for i in range(len(eda["values"])):
                    eda_data.append([eda_timestamp[i], eda["values"][i]])

                # temperature
                tmp = data["rawData"]["temperature"]
                tmp_timestamp = [round(tmp["timestampStart"] + i * (1e6 / tmp["samplingFrequency"])) for i in range(len(tmp["values"]))]
                for i in range(len(tmp["values"])):
                    temperature_data.append([tmp_timestamp[i], tmp["values"][i]])

                # bvp
                bvp = data["rawData"]["bvp"]
                bvp_timestamp = [round(bvp["timestampStart"] + i * (1e6 / bvp["samplingFrequency"])) for i in range(len(bvp["values"]))]
                for i in range(len(bvp["values"])):
                    bvp_data.append([bvp_timestamp[i], bvp["values"][i]])

                # systolic peaks
                sps = data["rawData"]["systolicPeaks"]
                for sp in sps["peaksTimeNanos"]:
                    systolic_peaks_data.append([sp])

                # steps
                steps = data["rawData"]["steps"]
                steps_timestamp = [round(steps["timestampStart"] + i * (1e6 / steps["samplingFrequency"])) for i in range(len(steps["values"]))]
                for i in range(len(steps["values"])):
                    steps_data.append([steps_timestamp[i], steps["values"][i]])

                # tags
                tags = data["rawData"]["tags"]
                for tag in tags["tagsTimeMicros"]:
                    tags_data.append([tag])

        except Exception as e:
            print(f"Error processing file {avro_file_path}: {e}")

    # to csv files
    sensor_data = [
        ('accelerometer.csv', ["unix_timestamp", "x", "y", "z"], accelerometer_data),
        ('gyroscope.csv', ["unix_timestamp", "x", "y", "z"], gyroscope_data),
        ('eda.csv', ["unix_timestamp", "eda"], eda_data),
        ('temperature.csv', ["unix_timestamp", "temperature"], temperature_data),
        ('bvp.csv', ["unix_timestamp", "bvp"], bvp_data),
        ('systolic_peaks.csv', ["systolic_peak_timestamp"], systolic_peaks_data),
        ('steps.csv', ["unix_timestamp", "steps"], steps_data),
        ('tags.csv', ["tags_timestamp"], tags_data),
    ]

    for filename, headers, data in sensor_data:
        with open(os.path.join(output_folder, filename), 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)

# folder paths
input_folder = os.path.expanduser("/Users/cadyngo/Desktop/Embrace Raw/0719")
output_folder = os.path.expanduser("/Users/cadyngo/Desktop/Empatica DATA/0719NEWEST")

# convert all avro files in the folder
process_avro_files(input_folder, output_folder)