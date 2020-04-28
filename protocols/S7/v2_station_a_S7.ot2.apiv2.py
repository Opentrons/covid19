from opentrons import protocol_api
import math
import json
import os

# metadata
metadata = {
    'protocolName': 'Version 2 S7 Station A',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 8  # start with 8 samples, slowly increase to 48, then 94 (max is 94)
SAMPLE_VOLUME = 200
ROBOT = 'A1'
TIP_TRACK = False
LYSIS_BUFFER_VOLUME = 200


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['1', '3', '4', '6'])
    ]
    dest_plate = ctx.load_labware('nest_96_deepwell_2ml', '2',
                                  '96-deepwell sample plate')
    tempdeck = ctx.load_module('Temperature Module Gen2', '7')
    tempdeck.set_temperature(4)
    reagent_block = tempdeck.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_screwcap',
        'chilled tubeblock for internal control (A1)')
    lys_buff = ctx.load_labware('opentrons_6_tuberack_falcon_50ml_conical',
                                '5',
                                'tuberack for lysis buffer (A1)').wells()[0]
    tipracks1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot,
                                     '1000µl filter tiprack')
                    for slot in ['8', '9']]
    tipracks20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot,
                                   '20µl filter tiprack')
                  for slot in ['10', '11']]

    # load pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'left', tip_racks=tipracks20)
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=tipracks1000)

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests = dest_plate.wells()[:NUM_SAMPLES]
    prot_k = reagent_block.wells()[0]
    iec = reagent_block.wells()[1]

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
                    tip_log['count'][p20] = data['tips20']
                else:
                    tip_log['count'][p20] = 0
        else:
            tip_log['count'] = {p1000: 0, p20: 0}
    else:
        tip_log['count'] = {p1000: 0, p20: 0}

    tip_log['tips'] = {
        pip: [tip for rack in rackset for tip in rack.wells()]
        for pip, rackset in zip([p1000, p20], [tipracks1000, tipracks20])
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [p1000, p20]
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

    heights = {lys_buff: 60}
    radius = (lys_buff.diameter)/2
    min_h = 5

    def h_track(vol):
        nonlocal heights
        dh = vol/(math.pi*(radius**2))
        if heights[lys_buff] - dh > min_h:
            heights[lys_buff] = heights[lys_buff] - dh
        else:
            heights[lys_buff] = 5
        return lys_buff.bottom(heights[lys_buff])

    # transfer samples
    for s, d in zip(sources, dests):
        if not p1000.hw_pipette['has_tip']:
            pick_up(p1000)
        p1000.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p1000.blow_out(d.top(-2))
        p1000.aspirate(100, d.top())
        p1000.drop_tip()

    # transfer lysis buffer
    for i, d in enumerate(dests):
        pick_up(p1000)
        p1000.transfer(LYSIS_BUFFER_VOLUME, h_track(LYSIS_BUFFER_VOLUME),
                       d.bottom(5), mix_after=(5, 200), new_tip='never')
        p1000.blow_out(d.top(-2))
        p1000.aspirate(100, d.top())
        p1000.drop_tip()

    # transfer proteinase K
    for d in dests:
        pick_up(p20)
        p20.transfer(10, prot_k, d.bottom(5), air_gap=5,
                     new_tip='never')
        p20.blow_out(d.top(-2))
        p20.aspirate(10, d.top())
        p20.drop_tip()

    ctx.delay(minutes=25, msg='Delaying 25 minutes before addition of IEC.')

    # transfer IEC
    for d in dests:
        pick_up(p20)
        p20.transfer(10, iec, d.bottom(5), air_gap=5,
                     new_tip='never')
        p20.blow_out(d.top(-2))
        p20.aspirate(10, d.top())
        p20.drop_tip()

    ctx.comment('Move deepwell plate (slot 2) to Station B for RNA \
extraction.')

    # track final used tip
    if TIP_TRACK and not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips1000': tip_log['count'][p1000],
            'tips20': tip_log['count'][p20]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
