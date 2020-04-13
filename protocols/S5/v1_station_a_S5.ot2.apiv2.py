from opentrons import protocol_api
import math

# metadata
metadata = {
    'protocolName': 'S5 Station A Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

NUM_SAMPLES = 30
SAMPLE_VOLUME = 200


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['10', '7', '4', '1'])
    ]
    dest_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '2',
        '96-deepwell sample plate')
    reagent_rack = ctx.load_labware('opentrons_6_tuberack_falcon_50ml_conical',
                                    '5', 'lysis buffer tuberack')
    tipracks1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot,
                                     '1000µl filter tiprack')
                    for slot in ['6', '9']]

    # load pipette
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=tipracks1000)

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests = dest_plate.wells()[:NUM_SAMPLES]

    lys_buff = reagent_rack.wells()[:2]
    heights = {tube: 60 for tube in lys_buff}
    radius = (lys_buff[0].diameter)/2
    min_h = 5

    def h_track(tube, vol):
        nonlocal heights
        dh = vol/(math.pi*(radius**2))
        if heights[tube] - dh > min_h:
            heights[tube] = heights[tube] - dh
        else:
            heights[tube] = 5
        return tube.bottom(heights[tube])

    # transfer lysis buffer
    p1000.pick_up_tip()
    for i, d in enumerate(dests):
        source = lys_buff[i//48]
        p1000.transfer(528, h_track(source, 528), d.bottom(2), air_gap=100,
                       new_tip='never',)
        p1000.blow_out(d.top(-2))

    # transfer samples
    for s, d in zip(sources, dests):
        if not p1000.hw_pipette['has_tip']:
            p1000.pick_up_tip()
        p1000.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p1000.aspirate(100, d.top())
        p1000.drop_tip()
