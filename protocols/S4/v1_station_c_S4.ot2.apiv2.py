from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S4 Station C Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 5 2ml tuberack:
    - mastermixes: tubes A1-A3 for 3 mastermixes, A1-A2 for 2 mastermixes
    - positive control: tube B1
    - negative control: tube B2
"""

NUM_SAMPLES = 30
NUM_MASTERMIX = 3  # should be 2 or 3


def run(ctx: protocol_api.ProtocolContext):
    source_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '1',
        'RNA elution plate from station B')
    tempdeck = ctx.load_module('tempdeck', '4')
    pcr_plate = tempdeck.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', 'PCR plate')
    tempdeck.set_temperature(4)
    tuberack = ctx.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap', '7',
        '2ml screw tuberack for mastermix')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['2', '5', '8']
    ]

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)

    # setup up sample sources and destinations
    samples = source_plate.wells()[:NUM_SAMPLES]
    sample_dest_sets = [
        row[i*NUM_MASTERMIX:(i+1)*NUM_MASTERMIX]
        for i in range(12//NUM_MASTERMIX)
        for row in pcr_plate.rows()
    ][:NUM_SAMPLES]
    mm = tuberack.rows()[0][:NUM_MASTERMIX]
    mm_dests = [
        [well for col in pcr_plate.columns()[j::NUM_MASTERMIX]
            for well in col][:NUM_SAMPLES] + pcr_plate.columns()[9+j][-2:]
        for j in range(NUM_MASTERMIX)
    ]
    pos_control = tuberack.rows()[1][0]
    pos_control_dests = pcr_plate.rows()[-2][-1*NUM_MASTERMIX:]
    neg_control = tuberack.rows()[1][1]
    neg_control_dests = tuberack.rows()[-1][-1*NUM_MASTERMIX:]

    # transfer mastermixes
    for s, d_set in zip(mm, mm_dests):
        p20.transfer(20, s, d_set)

    # transfer samples to corresponding locations
    for s, d_set in zip(samples, sample_dest_sets):
        for d in d_set:
            p20.pick_up_tip()
            p20.transfer(5, s, d, new_tip='never')
            p20.mix(1, 10, d)
            p20.blow_out(d.top(-2))
            p20.aspirate(5, d.top(2))
            p20.drop_tip()

    # transfer controls
    for d in pos_control_dests:
        p20.pick_up_tip()
        p20.transfer(5, pos_control, d, new_tip='never')
        p20.mix(1, 10, d)
        p20.blow_out(d.top(-2))
        p20.aspirate(5, d.top(2))
        p20.drop_tip()

    for d in neg_control_dests:
        p20.pick_up_tip()
        p20.transfer(5, neg_control, d, new_tip='never')
        p20.mix(1, 10, d)
        p20.blow_out(d.top(-2))
        p20.aspirate(5, d.top(2))
        p20.drop_tip()
