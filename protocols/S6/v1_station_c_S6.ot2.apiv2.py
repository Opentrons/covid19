from opentrons import protocol_api
import math

# metadata
metadata = {
    'protocolName': 'S6 Station C Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

"""
REAGENT SETUP (For Samples Greater than 32 Target):

- slot 7 2ml tuberack:
    - mastermixes: tubes A1-C1 for up to 3 mastermixes
- slot 5 pcr strip aluminum block:
    - Control: Column 4. Control can be oriented however you like.

REAGENT SETUP (For Samples Less than 32 Target):
- slot 5 pcr strip aluminum block:
    - mastermix: Columns 1-3 have the three mastermixes, including dead volume.
    - Control: Column 4. Control can be oriented however you like.

"""

NUM_SAMPLES = 96
NUM_MASTERMIX = 3  # should be 2 or 3
VOL_SAMPLE = 3
VOL_CONTROL = 8
VOL_MASTERMIX = 5
DEAD_VOL = 3


def run(ctx: protocol_api.ProtocolContext):
    tempdeck = ctx.load_module('tempdeck', '1')
    source_plate = tempdeck.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt',
        'RNA elution plate from station B')
    pcr_plate = ctx.load_labware(
        'appliedbiosystems_384_wellplate_40ul', '2', 'PCR plate')
    strips = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '5',
        'strips for mastermix and controls')
    tips300s = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '4')]
    tips20m = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3', '6', '9', '10']
    ]
    tuberack = ctx.load_labware(
        'mhs_24_tuberack_2ml', '7', '2ml Eppendorf tuberack')

    # pipette
    p300 = ctx.load_instrument('p300_single_gen2', 'right', tip_racks=tips300s)
    m20 = ctx.load_instrument('p20_multi_gen2', 'left', tip_racks=tips20m)

    # setup up sample sources and destinations
    num_cols = math.ceil(NUM_SAMPLES/8)
    samples = source_plate.rows()[0][:num_cols]

    # PCR plate set up with triplicates moving across the columns, then
    # down the plate.
    rowA = []
    rowB = []
    for col in pcr_plate.columns():
        rowA.append(col[0].bottom(2))
        rowB.append(col[1].bottom(2))
    sample_dest_sets = rowA + rowB

    mm = tuberack.wells()[:NUM_MASTERMIX]

    # Configure mastermix to distribute every three columns, given the
    # number of samples required.
    mm_sample_repeat = NUM_SAMPLES//8*3
    mm1_dest = sample_dest_sets[0:mm_sample_repeat:3]
    mm2_dest = sample_dest_sets[1:mm_sample_repeat:3]
    mm3_dest = sample_dest_sets[2:mm_sample_repeat:3]
    controls = strips.rows()[0][-1]

    mm_strips = strips.columns()[:NUM_MASTERMIX]
    if NUM_SAMPLES >= 32:
        # transfer mastermixes to strip
        vol_mm_per_strip_well = NUM_SAMPLES*VOL_MASTERMIX/8 + DEAD_VOL
        for master, strip in zip(mm, mm_strips):
            p300.pick_up_tip()
            for well in strip:
                p300.aspirate(vol_mm_per_strip_well, master.bottom(.25))
                p300.dispense(vol_mm_per_strip_well, well.bottom(2))
                p300.blow_out(well.bottom(4))
            p300.drop_tip()

    # transfer mastermix from strips to PCR plate
    m20.pick_up_tip()
    for d in mm1_dest:
        m20.aspirate(VOL_MASTERMIX, mm_strips[0][0].bottom(.1))
        m20.air_gap(2)
        m20.dispense(VOL_MASTERMIX, d)
        m20.blow_out(d.labware.bottom(3))
    m20.drop_tip()

    m20.pick_up_tip()
    for d in mm2_dest:
        m20.aspirate(VOL_MASTERMIX, mm_strips[1][0].bottom(.1))
        m20.air_gap(2)
        m20.dispense(VOL_MASTERMIX, d)
        m20.blow_out(d.labware.bottom(3))
    m20.drop_tip()

    m20.pick_up_tip()
    for d in mm3_dest:
        m20.aspirate(VOL_MASTERMIX, mm_strips[2][0].bottom(.1))
        m20.air_gap(2)
        m20.dispense(VOL_MASTERMIX, d)
        m20.blow_out(d.labware.bottom(3))
    m20.drop_tip()

    # transfer samples to corresponding locations
    for idx, s in enumerate(samples):
        curr_idx = 3*idx
        for d in sample_dest_sets[curr_idx:curr_idx+3]:
            m20.pick_up_tip()
            m20.transfer(VOL_SAMPLE, s, d, new_tip='never', air_gap=2)
            m20.mix(1, 5, d)
            m20.blow_out(d.labware.bottom(5))
            m20.aspirate(5, d.labware.top(1))
            m20.drop_tip()

    # transfer controls
    m20.pick_up_tip()
    m20.aspirate(VOL_SAMPLE, controls)
    m20.dispense(VOL_SAMPLE, pcr_plate.rows()[1][-1].bottom(2))
    m20.blow_out(pcr_plate.rows()[1][-1].bottom(5))
    m20.air_gap(2)
    m20.drop_tip()
