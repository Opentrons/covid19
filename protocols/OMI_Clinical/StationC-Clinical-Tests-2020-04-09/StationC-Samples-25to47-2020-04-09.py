metadata = {
    'protocolName': 'BP Genomics Station C',
    'author': 'Chaz <chaz@opentrons.com; Anton <acjs@stanford.edu>',
    'source': 'COVID-19 Project',
    'apiLevel': '2.2'
}

# Protocol constants
QPCR_LABWARE = 'ab_96_aluminumblock'

MASTER_MIX_MAP = '''
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
Reaction	Reaction	Endogenous	Reaction	Reaction	Endogenous
'''

SAMPLE_MAP = '''
Sample 25	Sample 25	Sample 25	Sample 33	Sample 33	Sample 33	Sample 41	Sample 41	Sample 41	PCD 4	Negative	Negative
Sample 26	Sample 26	Sample 26	Sample 34	Sample 34	Sample 34	Sample 42	Sample 42	Sample 42	PCD 4	Negative	Negative
Sample 27	Sample 27	Sample 27	Sample 35	Sample 35	Sample 35	Sample 43	Sample 43	Sample 43
Sample 28	Sample 28	Sample 28	Sample 36	Sample 36	Sample 36	Sample 44	Sample 44	Sample 44
Sample 29	Sample 29	Sample 29	Sample 37	Sample 37	Sample 37	Sample 45	Sample 45	Sample 45
Sample 30	Sample 30	Sample 30	Sample 38	Sample 38	Sample 38	Sample 46	Sample 46	Sample 46
Sample 31	Sample 31	Sample 31	Sample 39	Sample 39	Sample 39	Sample 47	Sample 47	Sample 47
Sample 32	Sample 32	Sample 32	Sample 40	Sample 40	Sample 40						
'''

# Master mix locations on the eppendorf tube holder
REAGENT_LOCATIONS = {
    'Reaction': 'A1',
    'Endogenous': 'B1',
    'Standard': 'B2',
    'Water': 'B3',
    'Negative': 'B3', # Synonym for water
    'IEC RNA': 'C1',
    'PCD 8': 'C5',
    'PCD 7': 'C6',
    'PCD 6': 'D1',
    'PCD 5': 'D2',
    'PCD 4': 'D3',
    'PCD 3': 'D4',
    'PCD 2': 'D5',
    'PCD 1': 'D6'
}

# Transfer volumes
MIX_VOLUME = 15
SAMPLE_VOLUME = 5

# Tip locations
SAMPLE_TIP_LOCATIONS = ['3', '6']

import re
import itertools

def transfer_with_primitives(p, source, dest, volume=SAMPLE_VOLUME, mix=19):
    p.pick_up_tip()

    p.aspirate(1, source)
    for _ in range(2):
        p.aspirate(mix, source)
        p.dispense(mix, source)

    p.aspirate(volume - 1, source)
    p.dispense(volume - 1, dest)

    for _ in range(2):
        p.aspirate(mix, dest)
        p.dispense(mix, dest)

    p.dispense(1, dest)
    p.blow_out(dest.top())
    p.air_gap(3, -1)
    p.drop_tip()

def run(protocol):
    sample_tip_racks = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_20ul', s) for s in SAMPLE_TIP_LOCATIONS
            ]
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=sample_tip_racks)

    tempdeck = protocol.load_module('tempdeck', '4')
    tempdeck.set_temperature(4)

    tempplate = tempdeck.load_labware(
        QPCR_LABWARE)

    tempplate_wells_by_row = list(itertools.chain(*tempplate.rows()))

    reagent_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', 5)

    elution_plate = protocol.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '1', 'Elution Plate')

    p20.flow_rate.aspirate = 10
    p20.flow_rate.dispense = 15
    p20.flow_rate.blow_out = 50

    # Distribute Master Mixes
    # Split up the master mix map into a list
    master_mix_labels = [""] *  12*8
    for i, row in enumerate(MASTER_MIX_MAP.strip('\n ').split('\n')):
        for j, label in enumerate(row.split('\t')):
            master_mix_labels[i*12+j] = label

    master_mix_wells = dict()

    # Figure out unique master mixes on the map, so we can use a single
    # tip for each
    for mix in set(master_mix_labels):
        if mix == '':
            continue
        master_mix_wells[mix] = list()

    for mix, well in zip(master_mix_labels, tempplate_wells_by_row):
        if mix == '':
            continue
        master_mix_wells[mix].append(well)

    # Do the master mix transfer
    for mix, wells in master_mix_wells.items():
        p20.pick_up_tip()
        for well in wells:
            p20.transfer(MIX_VOLUME, reagent_rack[REAGENT_LOCATIONS[mix]], well, new_tip='never')
            p20.blow_out(well.top())
        p20.drop_tip()

    # Transfer the samples and controls
    # Same deal as above, except every transfer gets its own tip,
    # which makes it easier because we don't bother optimizing for tip use.
    # Transfers are made row by row, left to right.

    sample_labels = [""] *  12*8
    for i, row in enumerate(SAMPLE_MAP.strip('\n ').split('\n')):
        for j, label in enumerate(row.split('\t')):
            sample_labels[i*12+j] = label

    sample_wells = zip(sample_labels, tempplate_wells_by_row)
    for sample, dest_well in sample_wells:
        # Determine whether we are dealing with an actual sample, which we
        # will take from the input sample plate; or a control, which we will
        # take from a location on the reagent rack. We expect samples to be
        # numbered, and will take the sample from the well matching the sample
        # number (eg Sample 1 = well 1 = plate.wells()[0])

        if sample == '':
            continue

        sample_match = re.match(r'Sample ([0-9]+)', sample)
        if sample_match:
            source_well = elution_plate.wells()[int(sample_match.groups()[0]) - 1]
        else:
            source_well = reagent_rack[REAGENT_LOCATIONS[sample]]

        transfer_with_primitives(p20, source_well, dest_well)
