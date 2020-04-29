from opentrons import protocol_api
import json
import os

# metadata
metadata = {
    'protocolName': 'Version 2 S7 Station C BP Genomics',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 8  # start with 8 samples, slowly increase to 48, then 94 (max is 94)
PREPARE_MASTERMIX = True
TIP_TRACK = False
SAMPLE_VOL = 5


def run(ctx: protocol_api.ProtocolContext):
    global MM_TYPE

    # check source (elution) labware type
    source_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '1',
        'chilled elution plate on block from Station B')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3', '6', '7', '8', '9', '10', '11']
    ]
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '2')]
    tempdeck = ctx.load_module('Temperature Module Gen2', '4')
    pcr_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', 'PCR plate')
    tempdeck.set_temperature(4)
    tube_block = ctx.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_screwcap', '5',
        '2ml screw tube aluminum block for mastermix + controls')

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)

    # setup up sample sources and destinations
    sources = source_plate.wells()[:NUM_SAMPLES]
    sample_dests = pcr_plate.wells()[:NUM_SAMPLES]

    tip_log = {'count': {}}
    folder_path = '/data/C'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips20' in data:
                    tip_log['count'][p20] = data['tips20']
                else:
                    tip_log['count'][p20] = 0
                if 'tips300' in data:
                    tip_log['count'][p300] = data['tips300']
                else:
                    tip_log['count'][p300] = 0
        else:
            tip_log['count'] = {p20: 0, p300: 0}
    else:
        tip_log['count'] = {p20: 0, p300: 0}

    tip_log['tips'] = {
        p20: [tip for rack in tips20 for tip in rack.wells()],
        p300: [tip for rack in tips300 for tip in rack.wells()]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [p20, p300]
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

    """ mastermix component maps """
    mm_tube = tube_block.wells()[0]
    mm_dict = {
        'volume': 15,
        'components': {
            tube: vol
            for tube, vol in zip(tube_block.columns()[1], [10, 1, 1, 3])
        }
    }

    if PREPARE_MASTERMIX:

        # create mastermix
        for tube, vol in mm_dict['components'].items():
            mm_vol = vol*NUM_SAMPLES*1.1
            disp_loc = mm_tube.bottom(5) if mm_vol < 50 else mm_tube.top(-5)
            pip = p300 if mm_vol > 20 else p20
            pick_up(pip)
            pip.transfer(mm_vol, tube.bottom(2), disp_loc, new_tip='never')
            pip.drop_tip()

    # transfer mastermix
    mm_vol = mm_dict['volume']
    mm_dests = [d.bottom(2) for d in sample_dests + pcr_plate.wells()[NUM_SAMPLES:NUM_SAMPLES+2]
    p20.transfer(mm_vol, mm_tube, mm_dests)

    # transfer samples to corresponding locations
    for s, d in zip(sources, sample_dests):
        pick_up(p20)
        p20.transfer(SAMPLE_VOL, s.bottom(2), d.bottom(2), new_tip='never')
        p20.mix(1, 10, d.bottom(2))
        p20.blow_out(d.top(-2))
        p20.aspirate(5, d.top(2))  # suck in any remaining droplets on way to trash
        p20.drop_tip()

    # transfer positive and negative controls
    for s, d in zip(tube_block.columns()[0][1:3],
                    pcr_plate.wells()[NUM_SAMPLES:NUM_SAMPLES+2]):
        pick_up(p20)
        p20.transfer(SAMPLE_VOL, s.bottom(2), d.bottom(2), new_tip='never')
        p20.mix(1, 10, d.bottom(2))
        p20.blow_out(d.top(-2))
        p20.aspirate(5, d.top(2))  # suck in any remaining droplets on way to trash
        p20.drop_tip()

    # track final used tip
    if TIP_TRACK and not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips20': tip_log['count'][p20],
            'tips300': tip_log['count'][p300]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
