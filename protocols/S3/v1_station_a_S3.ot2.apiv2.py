from opentrons import protocol_api
import json
import os

# metadata
metadata = {
    'protocolName': 'S3 Station A Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}

NUM_SAMPLES = 96
SAMPLE_VOLUME = 400
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['1', '3', '4', '7'])
    ]
    dest_plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '2',
        '96-deepwell sample plate')
    tipracks1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul',
                                     slot, '1000µl tiprack')
                    for slot in ['5', '6', '8', '9', '10', '11']]

    # load pipette
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=tipracks1000)

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests = [well for col in dest_plate.columns()[0::2] for well in col] + [
        well for col in dest_plate.columns()[1::2] for well in col]

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
        tip_log['count'][pip] += 1
        pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])

    # transfer
    for s, d in zip(sources, dests):
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
