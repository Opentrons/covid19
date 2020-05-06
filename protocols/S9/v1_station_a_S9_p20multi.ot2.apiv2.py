from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'S2 Station A Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

NUM_SAMPLES = 96
SAMPLE_VOLUME = 400
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    internal_control = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '1',
        'chilled tubeblock for internal control (strip 1)').wells()[0]
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['5', '6', '2', '3'])
    ]
    dest_plate = ctx.load_labware(
        'nest_96_deepwell_2ml', '4', '96-deepwell sample plate')
    lys_buff = ctx.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', '7',
        '50ml tuberack for lysis buffer + PK (tube A1)').wells()[0]
    # lys_buff = ctx.load_labware(
    #     'opentrons_24_aluminumblock_generic_2ml_screwcap', '7',
    #     '50ml tuberack for lysis buffer + PK (tube A1)').wells()[0]
    tipracks1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot,
                                     '1000µl filter tiprack')
                    for slot in ['8', '9', '11']]
    tipracks20 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '10',
                                   '20µl filter tiprack')]

    # load pipette
    m20 = ctx.load_instrument('p20_multi_gen2', 'left', tip_racks=tipracks20)
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=tipracks1000)

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests_single = dest_plate.wells()[:NUM_SAMPLES]
    dests_multi = dest_plate.rows()[0][:math.ceil(NUM_SAMPLES)]

    tip_log = {'count': {}}
    folder_path = '/data/A'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips1000' in data:
                    tip_log['count'][p1000] = data['tips1000']
                else:
                    tip_log['count'][p1000] = 0
                if 'tips20' in data:
                    tip_log['count'][m20] = data['tips20']
                else:
                    tip_log['count'][m20] = 0
    else:
        tip_log['count'] = {p1000: 0, m20: 0}

    tip_log['tips'] = {
        p1000: [tip for rack in tipracks1000 for tip in rack.wells()],
        m20: [tip for rack in tipracks20 for tip in rack.rows()[0]]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [p1000, m20]
    }

    def pick_up(pip):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
        tip_log['count'][pip] += 1

    heights = {lys_buff: 40}
    radius = (lys_buff.diameter)/2
    min_h = 5

    def h_track(tube, vol):
        nonlocal heights
        dh = vol/(math.pi*(radius**2))
        if heights[tube] - dh > min_h:
            heights[tube] = heights[tube] - dh
        else:
            heights[tube] = 5
        return tube.bottom(heights[tube])

    # transfer sample
    for s, d in zip(sources, dests_single):
        pick_up(p1000)
        p1000.transfer(SAMPLE_VOLUME, s.bottom(5), d.bottom(5), air_gap=100,
                       new_tip='never')
        p1000.air_gap(100)
        p1000.drop_tip()

    # transfer lysis buffer + proteinase K and mix
    for s, d in zip(sources, dests_single):
        pick_up(p1000)
        p1000.transfer(SAMPLE_VOLUME, s.bottom(5), d.bottom(5), air_gap=100,
                       mix_after=(10, 100), new_tip='never')
        p1000.air_gap(100)
        p1000.drop_tip()

    ctx.pause('Incubate sample plate (slot 4) at 55-57˚C for 20 minutes. \
Return to slot 4 when complete.')

    # transfer internal control
    for d in dests_multi:
        pick_up(m20)
        m20.transfer(10, internal_control, d.bottom(10), air_gap=5,
                     new_tip='never')
        m20.air_gap(5)
        m20.drop_tip()

    ctx.comment('Move deepwell plate (slot 4) to Station B for RNA \
extraction.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips1000': tip_log['count'][p1000],
            'tips20': tip_log['count'][m20]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
