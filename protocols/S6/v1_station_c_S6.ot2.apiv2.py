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
VOL_SAMPLE = 3
VOL_MASTERMIX = 5


def run(ctx: protocol_api.ProtocolContext):
    tempdeck = ctx.load_module('tempdeck', '1')
    source_plate = tempdeck.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt',
        'RNA elution plate from station B')
    pcr_plate = ctx.load_labware(
        'corning_384_wellplate_112ul_flat', '2', 'PCR plate')
    strips = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '5',
        'strips for mastermix and controls')
    tips300s = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '4')]
    tips20m = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3', '6', '9', '10']
    ]
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        '2ml Eppendorf tuberack')

    # pipette
    p300 = ctx.load_instrument('p300_single_gen2', 'right', tip_racks=tips300s)
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
        row[12*h_block:12*h_block+num_cols] for h_block in range(2)
        for row in pcr_plate.rows()[:2]][:NUM_MASTERMIX]
    controls = strips.rows()[0][NUM_MASTERMIX]

    # transfer mastermixes to strip
    vol_mm_per_strip_well = NUM_SAMPLES*VOL_MASTERMIX/8*1.1
    mm_strips = strips.columns()[:NUM_MASTERMIX]
    for s, strip in zip(mm, mm_strips):
        p300.transfer(vol_mm_per_strip_well, s, strip)

    # transfer mastermix from strips to PCR plate
    for s, d_set in zip(mm_strips, mm_dest_sets):
        m20.transfer(VOL_MASTERMIX, s, d_set, air_gap=2)

    # transfer samples to corresponding locations
    for s, d_set in zip(samples, sample_dest_sets):
        for d in d_set:
            m20.pick_up_tip()
            m20.transfer(VOL_SAMPLE, s, d, new_tip='never')
            m20.mix(1, 5, d)
            m20.blow_out(d.top(-2))
            m20.aspirate(5, d.top(2))
            m20.drop_tip()

    # transfer controls
    m20.transfer(VOL_SAMPLE, controls, pcr_plate.rows()[1][-1])
