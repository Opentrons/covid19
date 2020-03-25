metadata = {
    'protocolName': 'BP Genomics Station C',
    'author': 'Chaz <chaz@opentrons.com; Anton <acjs@stanford.edu>',
    'source': 'COVID-19 Project',
    'apiLevel': '2.2'
}

# Protocol constants
USING_THERMOCYCLER = False

# Master mix locations on the eppendorf tube holder
REAGENT_LOCATIONS = {
    'Endogenous': 'A1',
    'Reaction': 'A2',
    'Standard': 'A3',
    'Water': 'A4',
    'Control RNA': 'C1',
    'Control RNA 2': 'C2',
    'PCD 8': 'C5',
    'PCD 7': 'C6',
    'PCD 6': 'D1',
    'PCD 5': 'D2',
    'PCD 4': 'D3',
    'PCD 3': 'D4',
    'PCD 2': 'D5',
    'PCD 1': 'D6'
}

# Number of samples
# We expect that inbound samples are ordered numerically in well order
# Sample 1 in well 1, sample 2 in well 2, etc.
NUM_SAMPLES = 8

# Tip locations
SAMPLE_TIP_LOCATIONS = ['2', '3']

MASTER_MIX_MAP = '''
Endogenous	Reaction	Reaction	Reaction	Endogenous	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
Endogenous	Reaction	Reaction	Reaction	Endogenous	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
Endogenous	Reaction	Reaction	Reaction	Reaction	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
Endogenous	Reaction	Reaction	Reaction	Reaction	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
Endogenous	Reaction	Reaction	Reaction	Standard	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
Endogenous	Reaction	Reaction	Reaction	Standard	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
Endogenous	Reaction	Reaction	Reaction	Reaction	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
Endogenous	Reaction	Reaction	Reaction	Reaction	Reaction	Reaction	Standard	Standard	Standard	Standard	Standard
'''

SAMPLE_MAP = '''
Sample 1	Sample 1	Sample 1	Sample 1	Control RNA	Water	PCD 1	Water	PCD 1	Water	PCD 1	Water
Sample 2	Sample 2	Sample 2	Sample 2	Control RNA 2	Water	PCD 2	Water	PCD 2	Water	PCD 2	Water
Sample 3	Sample 3	Sample 3	Sample 3	Control RNA	Water	PCD 3	Water	PCD 3	Water	PCD 3	Water
Sample 4	Sample 4	Sample 4	Sample 4	Control RNA 2	Water	PCD 4	Water	PCD 4	Water	PCD 4	Water
Sample 5	Sample 5	Sample 5	Sample 5	Control RNA	Water	PCD 5	Water	PCD 5	Water	PCD 5	Water
Sample 6	Sample 6	Sample 6	Sample 6	Control RNA 2	Water	PCD 6	Water	PCD 6	Water	PCD 6	Water
Sample 7	Sample 7	Sample 7	Sample 7	Control RNA	Water	PCD 7	Water	PCD 7	Water	PCD 7	Water
Sample 8	Sample 8	Sample 8	Sample 8	Control RNA 2	Water	PCD 8	Water	PCD 8	Water	PCD 8	Water
'''

import re
import itertools

def transfer_with_primitives(p, source, dest, volume=5, mix=19):
    p.pick_up_tip()
    p.aspirate(volume, source)
    p.dispense(volume - 1, dest)
    for _ in range(4):
        p.aspirate(mix, dest)
        p.dispense(mix, dest)
    p.dispense(1, dest)
    p.blow_out(dest.top())
    p.drop_tip()

def run(protocol):
    sample_tip_racks = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_20ul', s) for s in SAMPLE_TIP_LOCATIONS
            ]
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=sample_tip_racks)

    if USING_THERMOCYCLER:
        tc = protocol.load_module('thermocycler')
        if tc.lid_position != 'open':
            tc.open_lid()
        tc.set_lid_temperature(105)
        tc.set_block_temperature(4)
        tempplate = tc.load_labware(
            'opentrons_96_aluminumblock_nest_wellplate_100ul')
    else:
        tempdeck = protocol.load_module('tempdeck', '4')
        tempdeck.set_temperature(4)
        tempplate = tempdeck.load_labware(
            'opentrons_96_aluminumblock_nest_wellplate_100ul')

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
    master_mix_labels = re.split(r'[\n\t]+', MASTER_MIX_MAP.strip())
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
            p20.transfer(15, reagent_rack[REAGENT_LOCATIONS[mix]], well, new_tip='never')
            p20.blow_out(well.top())
        p20.drop_tip()

    # Transfer the samples and controls
    # Same deal as above, except every transfer gets its own tip,
    # which makes it easier because we don't bother optimizing for tip use.
    # Transfers are made row by row, left to right.

    sample_labels = re.split(r'[\n\t]+', SAMPLE_MAP.strip())
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

    if USING_THERMOCYCLER:
        # thermocycler profile
        p1 = [
            {'temperature': 20, 'hold_time_minutes': 5},
            {'temperature': 45, 'hold_time_minutes': 20},
            {'temperature': 95, 'hold_time_minutes': 2}
        ]
        p2 = [
            {'temperature': 95, 'hold_time_seconds': 30},
            {'temperature': 63, 'hold_time_seconds': 50}
        ]
        tc.close_lid()
        tc.execute_profile(steps=p1, repetitions=1, block_max_volume=20)
        tc.execute_profile(steps=p2, repetitions=40, block_max_volume=20)
