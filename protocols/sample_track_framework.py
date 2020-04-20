import csv
import os
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Sample Tracking Framework',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}

"""

In order to use this feature, you will first have to upload a .csv file to the
`/data/` directory on your robot saved as BATCH.csv—— you can change the batch
ID on line 34. directory on your robot containing the following information for
each well containing sample in the starting labware. An example of this format
is as follows (including headers):

sample ID   slot    well
123         1       A1
456         1       B1
...

The output .csv map saved as BATCHOUTPUT.csv in the `/data/` diretory is
generated by zipping togther starting sample wells and output sample wells, and
tracing the ID of the output based on the ID of the input. This will vary from
protocol to protocol, but the input wells here are defined on line 60, and the
output wells on line 61.

"""

BATCH = 'test'


def run(ctx: protocol_api.ProtocolContext):

    example_source_labware = ctx.load_labware(
        'biorad_96_wellplate_200ul_pcr', '1')

    # parse input sample locations to first dictionary
    input_file_path = '/data/' + BATCH + '.csv'
    # input_file_path = BATCH + '.csv'
    if not os.path.isfile(input_file_path):
        raise Exception('No file for batch ' + BATCH)
    input_map = {}
    with open(input_file_path, 'r') as input_file:
        csv_reader = csv.reader(input_file)
        for i, line in enumerate(csv_reader):
            if i > 0 and line and line[0]:
                id, slot, well = [
                    val.strip().upper() for val in line[:3]]
                lw = ctx.loaded_labwares[int(slot)]
                input_map[lw.wells_by_name()[well]] = id

    # create transform map
    example_final_labware = ctx.load_module('tempdeck', '3').load_labware(
        'biorad_96_wellplate_200ul_pcr')
    input_wells = example_source_labware.wells()
    output_wells = [
        row[i*3:(i+1)*3]
        for i in range(4)
        for row in example_final_labware.rows()
    ]
    transform_map = {
        input: output
        for input, output in zip(input_wells, output_wells)
    }

    # find output wells of each sample
    output_map = {
        input_map[input]: transform_map[input]
        for input in input_map
    }

    # write output .csv file in same format
    output_file_path = '/data/' + BATCH + 'OUTPUT.csv'
    with open(output_file_path, 'w') as output_file:
        csv_writer = csv.writer(output_file)
        csv_writer.writerow(['sample ID', 'slot', 'well'])
        for key, value in output_map.items():
            # split values if multiple
            if isinstance(value, list):
                slots = [well._display_name.split()[-1] for well in value]
                wells = [well._display_name.split()[0] for well in value]
            else:
                slots = [value._display_name.split()[-1]]
                wells = [value._display_name.split()[0]]
            for s, w in zip(slots, wells):
                csv_writer.writerow([key, s, w])
