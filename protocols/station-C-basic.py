metadata = {
    'protocolName': 'BP Genomics Station C',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}

# Enter number of samples to run here
NUM_SAMPLES = 96
MASTERMIX_TIP_LOCATIONS = ['3']
SAMPLE_TIP_LOCATIONS = ['2']


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
    tempplate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul')

    reagent_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', 5)
    mastermix_tube = reagent_rack.wells('A1')

    tempwells = tempplate.wells()[:NUM_SAMPLES]
    tempdeck.set_temperature(4)

    elution_plate = protocol.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '1', 'Elution Plate')
    elutes = elution_plate.wells()[:NUM_SAMPLES]

    p20.flow_rate.aspirate = 10
    p20.flow_rate.dispense = 15
    p20.flow_rate.blow_out = 50

    # distribute mastermix
    p20.pick_up_tip(mastermix_tip)

    for well in tempwells:
        p20.transfer(15, mastermix_tube, well, new_tip='never')
        p20.blow_out(well.top())

    p20.drop_tip()

    # transfer 5ul of elutions to qPCR temp plate. Can change based on design
    for src, dest in zip(elutes, tempwells):
        p20.pick_up_tip()
        p20.aspirate(5, src)
        p20.dispense(4, dest)
        for _ in range(4):
            p20.aspirate(19, dest)
            p20.dispense(19, dest)
        p20.dispense(1, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()
