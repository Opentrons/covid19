from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'Version 1 S7 Station C BP Genomics',
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
        for slot in ['3', '6', '8', '9', '10', '11']
    ]
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '2')]
    tempdeck = ctx.load_module('Temperature Module Gen2', '4')
    pcr_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', 'PCR plate')
    mm_strips = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '7',
        'mastermix strips')
    tempdeck.set_temperature(4)
    tube_block = ctx.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_screwcap', '5',
        '2ml screw tube aluminum block for mastermix + controls')

    # pipette
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
        pip: len(tip_log['tips'][pip])
        for pip in [m20, p300]
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

        for i, (tube, vol) in enumerate(mm_dict['components'].items()):
            comp_vol = vol*(NUM_SAMPLES+2)*1.1  # 10% volume overage for samples + controls
            disp_loc = mm_tube.bottom(5) if comp_vol < 50 else mm_tube.top(-5)
            pick_up(p300)
            p300.transfer(comp_vol, tube.bottom(1), disp_loc, new_tip='never')
            if i < len(mm_dict['components'].items()) - 1:  # keep tip if last component
                p300.drop_tip()
        mm_total_vol = mm_dict['volume']*(NUM_SAMPLES+2)*1.3 # include mastermix volume overage
        if not p300.hw_pipette['has_tip']:  # pickup tip with P300 if necessary for mixing
            pick_up(p300)
        mix_vol = mm_total_vol / 2 if mm_total_vol / 2 <= 200 else 200  # mix volume is 1/2 MM total, maxing at 200µl
        p300.mix(15, mix_vol, mm_tube)
        # pip.blow_out(mm_tube.top(-2))

    # transfer mastermix to strips
    num_mm_dest_cols = math.ceil((NUM_SAMPLES+2)/8)
    vol_per_strip_well = num_mm_dest_cols*mm_dict['volume']*1.2
    mm_strip = mm_strips.columns()[0]
    if not p300.hw_pipette['has_tip']:
        pick_up(p300)
    for well in mm_strip:
        p300.transfer(vol_per_strip_well, mm_tube, well, new_tip='never')

    # transfer mastermix to plate
    mm_vol = mm_dict['volume']
    mm_dests = [d.bottom(2) for d in pcr_plate.rows()[0][:num_mm_dest_cols]]
    pick_up(m20)
    m20.transfer(mm_vol, mm_strip[0].bottom(0.5), mm_dests, new_tip='never')
    m20.drop_tip()

    # transfer samples to corresponding locations
    for s, d in zip(sources, sample_dests):
        pick_up(m20)
        m20.transfer(SAMPLE_VOL, s.bottom(2), d.bottom(2), new_tip='never')
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
