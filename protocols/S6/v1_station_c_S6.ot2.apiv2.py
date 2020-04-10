from opentrons import protocol_api
import math

# metadata
metadata = {
    'protocolName': 'S6 Station C Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}

"""
REAGENT SETUP:

- slot 5 2ml tuberack:
    - mastermixes: tubes A1-C1 for up to 3 mastermixes
    - positive control: tube A2
    - negative control: tube B2
"""

NUM_SAMPLES = 96
NUM_MASTERMIX = 3  # should be 2 or 3


def run(ctx: protocol_api.ProtocolContext):
    source_plate = ctx.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '1',
        'RNA elution plate from station B')
    pcr_plate = ctx.load_labware(
        'corning_384_wellplate_112ul_flat', '2', 'PCR plate')
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '5',
        '2ml Eppendorf tuberack')
    tips20s = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '4')]
    tips20m = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3', '6', '9']
    ]

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20s)
    m20 = ctx.load_instrument('p20_multi_gen2', 'left', tip_racks=tips20m)

    # setup up sample sources and destinations
    num_cols = math.ceil(NUM_SAMPLES/8)
    samples = source_plate.rows()[0][:num_cols]
    sample_dest_sets = [
        [well for col in pcr_plate.columns()[i::12]
         for well in col[:2]][:NUM_MASTERMIX]
        for i in range(num_cols)
    ]
    mm = tuberack.wells()[:NUM_MASTERMIX]
    mm_dest_sets = [
        [well for row in pcr_plate.rows()[v_block:v_block+3:2]
         for well in row[12*h_block:12*h_block+num_cols]]
        for h_block in range(2) for v_block in range(2)][:NUM_MASTERMIX]
    pos_control = tuberack.columns()[1][0]
    pos_control_dests = pcr_plate.rows()[-1][-6:NUM_MASTERMIX]
    neg_control = tuberack.columns()[1][1]
    neg_control_dests = pcr_plate.rows()[-1][-3:NUM_MASTERMIX]

    # transfer mastermixes
    for i, (s, d_set) in enumerate(zip(mm, mm_dest_sets)):
        control_dests = pcr_plate.rows()[0][-6+i::3]
        all_dests = d_set + control_dests
        p20.transfer(20, s, all_dests)

    # transfer samples to corresponding locations
    for s, d_set in zip(samples, sample_dest_sets):
        for d in d_set:
            m20.pick_up_tip()
            m20.transfer(5, s, d, new_tip='never')
            m20.mix(1, 10, d)
            m20.blow_out(d.top(-2))
            m20.aspirate(5, d.top(2))
            m20.drop_tip()

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
