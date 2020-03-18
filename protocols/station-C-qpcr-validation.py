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
INTERNAL_CONTROL_RNA_TUBES = [
    'C1', 'C2'
]

STANDARD_CURVE_TUBES = [
    'D6', 'D5', 'D4', 'D3', 'D2', 'D1', 'C6', 'C5'
]

# Number of samples
# We expect that inbound samples are ordered numerically in well order
# Sample 1 in well 1, sample 2 in well 2, etc.
NUM_SAMPLES = 8

# Tip locations
SAMPLE_TIP_LOCATIONS = ['2', '3']

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

    tempdeck = protocol.load_module('tempdeck', '4')
    # tempdeck.set_temperature(4)

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
        *tempplate.columns()[7],
        *tempplate.columns()[8],
        *tempplate.columns()[9],
        *tempplate.columns()[10],
        *tempplate.columns()[11]
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
            sample_destination = tempplate.rows()[sample_number][i]
            transfer_with_primitives(p20, sample_well, sample_destination)

    # Transfer control RNA into the control RNA wells
    for i in range(8):
        control_rna_well = reagent_rack[INTERNAL_CONTROL_RNA_TUBES[i % 2]]
        transfer_with_primitives(p20, control_rna_well, tempplate.columns()[4][i])

    # Transfer water into the negative control wells
    negative_control_wells = [
        *tempplate.columns()[5],
        *tempplate.columns()[7],
        *tempplate.columns()[9],
        *tempplate.columns()[11]
    ]
    for well in negative_control_wells:
        transfer_with_primitives(p20, reagent_rack[WATER_LOCATION], well)

    # Transfer standard curve into standard curve wells
    for curve_column in [6, 8, 10]:
        for dilution in range(8):
            transfer_with_primitives(
                p20,
                reagent_rack[STANDARD_CURVE_TUBES[dilution]],
                tempplate.columns()[curve_column][dilution])
