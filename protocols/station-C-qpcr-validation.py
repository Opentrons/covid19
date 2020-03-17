metadata = {
    'protocolName': 'BP Genomics Station C',
    'author': 'Chaz <chaz@opentrons.com; Anton <acjs@stanford.edu>',
    'source': 'COVID-19 Project',
    'apiLevel': '2.2'
}

# Protocol constants

# Master mix locations on the eppendorf tube holder
CONTROL_MIX_LOCATION = 'A1'
REACTION_MIX_LOCATION = 'A2'
STANDARD_CURVE_MIX_LOCATION = 'A3'
WATER_LOCATION = 'A4'

# Standard locations
INTERNAL_CONTROL_RNA_TUBES
STANDARD_CURVE_TUBES = []

# Number of samples
# We expect that inbound samples are ordered numerically in well order
# Sample 1 in well 1, sample 2 in well 2, etc.
NUM_SAMPLES = 8

# Tip locations
MASTERMIX_TIP_LOCATIONS = ['3']
SAMPLE_TIP_LOCATIONS = ['2']

def transfer_with_primitives(source, dest, volume=5, mix=19):
    p20.pick_up_tip()
    p20.aspirate(volume, source)
    p20.dispense(volume-1, dest)
    for _ in range(4):
        p20.aspirate(mix, dest)
        p20.dispense(mix, dest)
    p20.dispense(1, dest)
    p20.blow_out(dest.top())
    p20.drop_tip()

def run(protocol):
    mastermix_tip_rack = protocol.load_labware(
            'opentrons_96_filtertiprack_20ul', MASTERMIX_TIP_LOCATIONS[0]) #for s in MASTERMIX_TIP_LOCATIONS
    mastermix_tip = mastermix_tip_rack.wells()[0]

    sample_tip_racks = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_20ul', s) for s in SAMPLE_TIP_LOCATIONS
            ]
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=sample_tip_racks)

    tempdeck = protocol.load_module('tempdeck', '4')
    tempdeck.set_temperature(4)

    tempplate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul')

    reagent_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', 5)

    elution_plate = protocol.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '1', 'Elution Plate')

    p20.flow_rate.aspirate = 10
    p20.flow_rate.dispense = 15
    p20.flow_rate.blow_out = 50

    # Distribute Endogenous Control Master Mix
    p20.pick_up_tip()
    for well in [*tempplate.columns()[0], tempplate['A5'], tempplate['B5']]:
        p20.transfer(15, reagent_rack[CONTROL_MIX_LOCATION], well, new_tip='never')
        p20.blow_out(well.top())
    p20.drop_tip()

    # Distribute Reaction Master Mix
    p20.pick_up_tip()
    reaction_mix_wells = [
        *tempplate.columns()[1],
        *tempplate.columns()[2],
        *tempplate.columns()[3],
        tempplate['C5'], tempplate['D5'], tempplate['G5'], tempplate['H5'],
        *tempplate.columns()[5],
        *tempplate.columns()[6],
    ]

    for well in reaction_mix_wells:
        p20.transfer(15, reagent_rack[REACTION_MIX_LOCATION], well, new_tip='never')
        p20.blow_out(well.top())

    p20.drop_tip()

    # Distribute Standard Curve Mix
    p20.pick_up_tip()
    standard_curve_wells = [
        tempplate['E5'], tempplate['F5'],
        *tempplate.columns()[7:11]
    ]

    for well in standard_curve_wells:
        p20.transfer(15, reagent_rack[STANDARD_CURVE_MIX_LOCATION], well, new_tip='never')
        p20.blow_out(well.top())

    p20.drop_tip()

    # Take each sample and transfer 5 ul into each of
    # four wells: the human endogenous test well and
    # coronavirus wells in triplicate. Each sample will be
    # moved into a row corresponding to it's sample number:
    # Sample 1 = A1, A2, A3, A4; sample 2 = B1, B2, B3, B4
    sample_rna = elution_plate.wells()[:NUM_SAMPLES]
    for sample_number, sample_well in enumerate(sample_rna):
        for i in range(4):
            sample_destination = tempplate.rows()[0][i]
            transfer_with_primitives(sample_well, sample_destination)

    # Transfer control RNA into the control RNA wells
    for i in range(6):
        control_rna = INTERNAL_CONTROL_RNA[i // 2]
        transfer_with_primitives(control_rna_well, tempplate.columns(4)[i])

    # Transfer water into the negative control wells
    negative_control_wells = [
        tempplate['G5'], tempplate['H5'],
        *tempplate.columns(5),
        *tempplate.columns(7),
        *tempplate.columns(9),
        *tempplate.columns(11)
    ]
    for well in negative_control_wells:
        transfer_with_primitives(WATER_LOCATION, well)

    # Transfer standard curve into standard curve wells
    for curve_column in [6, 8, 10]:
        for dilution in range(8):
            transfer_with_primitives(STANDARD_CURVE_TUBES[dilution], tempplate.columns()[curve_column][dilution])
