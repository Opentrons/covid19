from opentrons import protocol_api
import json
import os

# metadata
metadata = {
    'protocolName': 'S2 Station A Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

slot 5 2ml screwcap tuberack:
    - internal control: tube A1

"""

NUM_SAMPLES = 8
SAMPLE_VOLUME = 300
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['1', '3', '4', '6'])
    ]
    dest_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '2',
        '96-deepwell sample plate')
    internal_control = ctx.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap', '5',
        'chilled tubeblock for internal control (A1)').wells()[0]
    tipracks1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot,
                                     '1000µl filter tiprack')
                    for slot in ['7', '8', '9']]
    tipracks20 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot,
                                   '20µl filter tiprack')
                  for slot in ['10', '11']]

    # load pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'left', tip_racks=tipracks20)
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=tipracks1000)

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests = [well for col in dest_plate.columns()[0::2] for well in col] + [
        well for col in dest_plate.columns()[1::2] for well in col]
    dests = dests[:NUM_SAMPLES]

    tip_log = {}
    file_path = '/data/A/tip_log.json'
    if tip_log and not ctx.is_simulating():
        if os.path.isfile(file_path):
            with open(file_path) as json_file:
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

    # transfer sample
    for s, d in zip(sources, dests):
        pick_up(p1000)
        p1000.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p1000.aspirate(100, d.top())
        p1000.drop_tip()

    # transfer internal control
    for d in dests:
        pick_up(p20)
        p20.transfer(10, internal_control, d.bottom(5), air_gap=5,
                     new_tip='never')
        p20.drop_tip()

    ctx.comment('Move deepwell plate (slot 2) to Station B for RNA \
extraction.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir('/data/A'):
            os.mkdir('/data/A')
        data = {
            'tips1000': tip_log['count'][p1000],
            'tips20': tip_log['count'][p20]
        }
        with open(file_path, 'w') as outfile:
            json.dump(data, outfile)
