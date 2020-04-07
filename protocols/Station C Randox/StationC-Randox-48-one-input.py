metadata = {
    'protocolName': 'Station C; Randox Pathway - 48 Samples',
    'author': 'Chaz <chaz@opentrons.com; Anton <acjs@stanford.edu>',
    'source': 'COVID-19 Project',
    'apiLevel': '2.2'
}

# Protocol constants
PCR_LABWARE = 'opentrons_96_aluminumblock_nest_wellplate_100ul'
'''PCR labware definition is based on anonymous plate. May need to change.'''
SAMPLE_NUMBER = 48


def run(protocol):
    tips = [protocol.load_labware('opentrons_96_filtertiprack_20ul', '3')]
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=tips)
    tempdeck = protocol.load_module('tempdeck', '4')
    protocol.comment('Setting temperature module to 4C')
    tempdeck.set_temperature(4)

    tempplate = tempdeck.load_labware(PCR_LABWARE)

    reagent_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '5')

    master_mix = reagent_rack['A1']

    elution_plate = protocol.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '1', 'Elution Plate')

    p20.flow_rate.aspirate = 10
    p20.flow_rate.dispense = 15
    p20.flow_rate.blow_out = 50

    tempplate_wells = tempplate.wells()[:SAMPLE_NUMBER]
    sample_wells = elution_plate.wells()[:SAMPLE_NUMBER]

    # Distribute Reaction Mix
    protocol.comment('Distributing master mix to 48 wells:')
    p20.pick_up_tip()
    for well in tempplate_wells:
        p20.transfer(15, master_mix, well, new_tip='never')
        p20.blow_out(well.top())
    p20.drop_tip()

    # Distribute and mix samples to wells in PCR plate
    msg = 'Adding samples from elution plate to plate with mastermix:'
    protocol.comment(msg)
    for idx, (src, dest) in enumerate(zip(sample_wells, tempplate_wells)):
        p20.pick_up_tip()
        protocol.comment(f'Mixing sample {idx+1}:')
        p20.aspirate(1, src)
        for _ in range(2):
            p20.aspirate(19, src)
            p20.dispense(19, src)

        protocol.comment(f'Transferring sample {idx+1}:')
        p20.aspirate(4, src)
        p20.dispense(4, dest)

        for _ in range(2):
            p20.aspirate(19, dest)
            p20.dispense(19, dest)

        p20.dispense(1, dest)
        p20.blow_out(dest.top(-1))
        p20.air_gap(3, -1)
        p20.drop_tip()
