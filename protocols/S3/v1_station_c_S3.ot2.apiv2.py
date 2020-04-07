from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S3 Station C Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.1'
}

"""
ElUTION_LABWARE must be one of the following:
    large strips
    short strips
    1.5ml tubes
    2ml tubes

MM_TYPE must be one of the following:
    MM1
    MM2
    MM3
"""

NUM_SAMPLES = 96
VOLUME_MMIX = 20
ELUTION_LABWARE = '2ml tubes'
PREPARE_MASTERMIX = True
MM_TYPE = 'MM1'

EL_LW_DICT = {
    'large strips': 'opentrons_96_aluminumblock_generic_pcr_strip_200ul',
    'short strips': 'opentrons_96_aluminumblock_generic_pcr_strip_200ul',
    '2ml tubes': 'opentrons_24_aluminumblock_generic_2ml_screwcap',
    '1.5ml tubes': 'opentrons_24_aluminumblock_nest_1.5ml_screwcap'
}


def run(ctx: protocol_api.ProtocolContext):

    # check source (elution) labware type
    if ELUTION_LABWARE not in EL_LW_DICT:
        raise Exception('Invalid ELUTION_LABWARE. Must be one of the \
following:\nlarge strips\nshort strips\n1.5ml tubes\n2ml tubes')

    source_racks = [
        ctx.load_labware(EL_LW_DICT[ELUTION_LABWARE], slot,
                         'RNA elution labware ' + str(i+1))
        for i, slot in enumerate(['4', '5', '1', '2'])
    ]
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['6', '9', '8', '7']
    ]
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '3')]
    tempdeck = ctx.load_module('tempdeck', '10')
    pcr_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul', 'PCR plate')
    tempdeck.set_temperature(4)
    mm_rack = ctx.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap', '11',
        '2ml screw tube aluminum block for mastermix')

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)

    # setup up sample sources and destinations
    if 'strips' in ELUTION_LABWARE:
        sources = [
            tube
            for i, rack in enumerate(source_racks)
            for col in [
                rack.columns()[c] if i % 2 == 0 else rack.columns()[c+1]
                for c in [0, 5, 10]
            ]
            for tube in col
        ][:NUM_SAMPLES]
        dests = pcr_plate.wells()[:NUM_SAMPLES]
    else:
        sources = [
            tube
            for rack in source_racks for tube in rack.wells()][:NUM_SAMPLES]
        dests = [
            well
            for h_block in range(2)
            for v_block in range(2)
            for col in pcr_plate.columns()[6*v_block:6*(v_block+1)]
            for well in col[4*h_block:4*(h_block+1)]][:NUM_SAMPLES]

    mm_tube = mm_rack.wells()[0]

    if PREPARE_MASTERMIX:
        """ mastermix component maps """
        mm1 = {
            tube: vol
            for tube, vol in zip(
                [well for col in mm_rack.columns()[2:5] for well in col][:10],
                [2.85, 12.5, 0.4, 1, 1, 0.25, 0.25, 0.5, 0.25, 1]
            )
        }
        mm2 = {
            tube: vol
            for tube, vol in zip(
                [mm_rack.wells_by_name()[well] for well in ['A3', 'C5', 'D5']],
                [10, 4, 1]
            )
        }
        mm3 = {
            tube: vol
            for tube, vol in zip(
                [mm_rack.wells_by_name()[well] for well in ['A6', 'B6']],
                [13, 2]
            )
        }
        mm_dict = {'MM1': mm1, 'MM2': mm2, 'MM3': mm3}

        # create mastermix
        for tube, vol in mm_dict[MM_TYPE].items():
            mm_vol = vol*(NUM_SAMPLES+5)
            disp_loc = mm_tube.bottom(5) if mm_vol < 50 else mm_tube.top(-5)
            pip = p300 if mm_vol > 20 else p20
            pip.transfer(mm_vol, tube.bottom(2), disp_loc, new_tip='once')

    # transfer mastermix
    for d in dests:
        p20.pick_up_tip()
        p20.transfer(VOLUME_MMIX, mm_tube, d.bottom(2), new_tip='never')
        p20.blow_out(d.bottom(5))
        p20.drop_tip()

    # transfer samples to corresponding locations
    for s, d in zip(sources, dests):
        p20.pick_up_tip()
        p20.transfer(5, s.bottom(2), d.bottom(2), new_tip='never')
        p20.mix(1, 10, d.bottom(2))
        p20.aspirate(5, d.top(2))
        p20.drop_tip()
