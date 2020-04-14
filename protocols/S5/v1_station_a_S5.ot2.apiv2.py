from opentrons import protocol_api
import math
import json
import os

# metadata
metadata = {
    'protocolName': 'S5 Station A Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

NUM_SAMPLES = 30
SAMPLE_VOLUME = 200
ROBOT = 'A1'
TIP_TRACK = False


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

    tip_log = {}
    file_path = '/data/A/tip_log.json'
    if tip_log and not ctx.is_simulating():
        if os.path.isfile(file_path):
            with open(file_path) as json_file:
                data = json.load(json_file)
                if 'tips1000' in data:
                    tip_log['count'] = {p1000: data['tips1000']}
                else:
                    tip_log['count'] = {p1000: 0}
    else:
        tip_log['count'] = {p1000: 0}

    tip_log['tips'] = {
        p1000: [tip for rack in tipracks1000 for tip in rack.wells()]}
    tip_log['max'] = {p1000: len(tip_log['tips'][p1000])}

    def pick_up(pip):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
    resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
        tip_log['count'][pip] += 1

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
    pick_up(p1000)
    for i, d in enumerate(dests):
        source = lys_buff[i//48]
        p1000.transfer(528, h_track(source, 528), d.bottom(2), air_gap=100,
                       new_tip='never',)
        p1000.blow_out(d.top(-2))

    # transfer samples
    for s, d in zip(sources, dests):
        if not p1000.hw_pipette['has_tip']:
            pick_up(p1000)
        p1000.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p1000.aspirate(100, d.top())
        p1000.drop_tip()

    # track final used tip
    if not ctx.is_simulating():
        data = {'tips1000': tip_log['count'][p1000]}
        with open(file_path, 'w') as outfile:
            json.dump(data, outfile)
