from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'Version 1 S8 Station C Ab Analytica P20MULTI',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 94  # start with 8 samples, slowly increase to 48, then 94 (max is 94)
PREPARE_MASTERMIX = True
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):
    global MM_TYPE

    # check source (elution) labware type
    source_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '1',
        'chilled elution plate on block from Station B')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3', '6', '8', '9', '10', '11']
    ]
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '2')]
    tempdeck = ctx.load_module('Temperature Module Gen2', '4')
    pcr_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', 'PCR plate')
    mm_strip_block = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '7',
        'mastermix strips')
    tempdeck.set_temperature(4)
    tube_block = ctx.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_screwcap', '5',
        '2ml screw tube aluminum block for mastermix + controls')

    # p300ette
    m20 = ctx.load_instrument('p20_multi_gen2', 'right', tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)

    # setup up sample sources and destinations
    num_cols = math.ceil(NUM_SAMPLES/8)
    sources = source_plate.rows()[0][:num_cols]
    sample_dests = pcr_plate.rows()[0][:num_cols]

    tip_log = {'count': {}}
    folder_path = '/data/C'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips20' in data:
                    tip_log['count'][m20] = data['tips20']
                else:
                    tip_log['count'][m20] = 0
                if 'tips300' in data:
                    tip_log['count'][p300] = data['tips300']
                else:
                    tip_log['count'][p300] = 0
        else:
            tip_log['count'] = {m20: 0, p300: 0}
    else:
        tip_log['count'] = {m20: 0, p300: 0}

    tip_log['tips'] = {
        m20: [tip for rack in tips20 for tip in rack.rows()[0]],
        p300: [tip for rack in tips300 for tip in rack.wells()]
    }
    tip_log['max'] = {
        p300: len(tip_log['tips'][p300])
        for p300 in [m20, p300]
    }

    def pick_up(p300):
        nonlocal tip_log
        if tip_log['count'][p300] == tip_log['max'][p300]:
            ctx.pause('Replace ' + str(p300.max_volume) + 'µl tipracks before \
resuming.')
            p300.reset_tipracks()
            tip_log['count'][p300] = 0
        p300.pick_up_tip(tip_log['tips'][p300][tip_log['count'][p300]])
        tip_log['count'][p300] += 1

    """ mastermix component maps """
    mm_tubes = tube_block.wells()[:2]
    mm_dict = {
        'volume': 20,
        'components': {
            tube: vol
            for tube, vol in zip(tube_block.columns()[1][:2], [17.5, 2.5])
        }
    }
    vol_overage = 1.2
    mm_tube_dests = mm_tubes[:1] if NUM_SAMPLES <= 72 else mm_tubes

    if PREPARE_MASTERMIX:
        # reduce overage to 10% volume if more than 48 samples
        for i, (tube, vol) in enumerate(mm_dict['components'].items()):
            pick_up(p300)
            comp_vol = vol*(NUM_SAMPLES+2)*vol_overage  # 10% volume overage for samples + controls
            mm_tube_vol = comp_vol/len(mm_tube_dests)
            num_trans = math.ceil(mm_tube_vol/160)
            vol_per_trans = mm_tube_vol/num_trans
            for d in mm_tube_dests:
                for _ in range(num_trans):
                    p300.air_gap(20)
                    p300.aspirate(vol_per_trans, tube)
                    ctx.delay(seconds=3)
                    p300.touch_tip(tube)
                    p300.air_gap(20)
                    p300.dispense(20, d.top())  # void air gap
                    p300.dispense(vol_per_trans, d.bottom(2))
                    p300.dispense(20, d.top())  # void pre-loaded air gap
                    p300.blow_out(d.top())
                    p300.touch_tip(d)
            if i < len(mm_dict['components'].items()) - 1:  # keep tip if last component
                p300.drop_tip()
        for d in mm_tube_dests:
            p300.mix(15, 200, d)
        # p300.blow_out(mm_tube.top(-2))

    # transfer mastermix to strips
    num_mm_dest_cols = math.ceil((NUM_SAMPLES+2)/8)
    num_dest_strips = 1 if NUM_SAMPLES <= 72 else 2
    vol_per_strip_well = num_mm_dest_cols*mm_dict['volume']*((vol_overage-1)/2+1)
    vol_per_strip_well /= num_dest_strips
    mm_strips = mm_strip_block.columns()[:num_dest_strips]
    if not p300.hw_pipette['has_tip']:
        pick_up(p300)
    for mm_tube, strip in zip(mm_tube_dests, mm_strips):
        for well in strip:
            p300.transfer(vol_per_strip_well, mm_tube, well, new_tip='never')

    # transfer mastermix to plate
    mm_vol = mm_dict['volume']
    mm_dests = [d.bottom(2) for d in pcr_plate.rows()[0][:num_mm_dest_cols]]
    pick_up(m20)
    for i, m in enumerate(mm_dests):
        if NUM_SAMPLES <= 72:
            source = mm_strips[0][0]
        else:
            source = mm_strips[i//(len(mm_dests)//2)][0]
        m20.transfer(mm_vol, source.bottom(0.5), mm_dests, new_tip='never')
    m20.drop_tip()

    # transfer samples to corresponding locations
    sample_vol = 30 - mm_vol
    for s, d in zip(sources, sample_dests):
        pick_up(m20)
        m20.transfer(sample_vol, s.bottom(2), d.bottom(2), new_tip='never')
        m20.mix(1, 10, d.bottom(2))
        m20.blow_out(d.top(-2))
        m20.aspirate(5, d.top(2))  # suck in any remaining droplets on way to trash
        m20.drop_tip()

    # NOTE: transfer positive and negative controls manually

    # track final used tip
    if TIP_TRACK and not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips20': tip_log['count'][m20],
            'tips300': tip_log['count'][p300]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
