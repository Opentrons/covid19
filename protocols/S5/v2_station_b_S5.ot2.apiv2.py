import math
from opentrons.types import Point
from opentrons import protocol_api
import os
import json

# metadata
metadata = {
    'protocolName': 'S5 Station B Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - VHB buffer: channels 1-3
    - SPR wash buffer: channel 4
    - wash 1: channels 5-8
    - wash 2: channels 9-12

"""

NUM_SAMPLES = 30
ELUTION_VOL = 50
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    tempdeck = ctx.load_module('tempdeck', '1')
    tempdeck.set_temperature(4)
    elution_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul',
        'cooled elution plate')
    reagent_res = ctx.load_labware(
        'nest_12_reservoir_15ml', '2', 'reagent reservoir')
    magdeck = ctx.load_module('magdeck', '4')
    magplate = magdeck.load_labware('usascientific_96_wellplate_2.4ml_deep')
    waste = ctx.load_labware(
        'nest_1_reservoir_195ml', '7', 'waste reservoir').wells()[0].top()
    tips300 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul', slot, '200µl filter tiprack')
        for slot in ['3', '6', '8', '9']
    ]
    tips1000 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
        for slot in ['10', '11']
    ]

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    # mag_samples_m = [
    #     well for well in
    #     magplate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]
    # elution_samples_m = [
    #     well for well in
    #     elution_plate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]
    mag_samples_m = magplate.rows()[0][:num_cols]
    mag_samples_s = magplate.wells()[:NUM_SAMPLES]
    elution_samples_m = elution_plate.rows()[0][:num_cols]

    vhb = reagent_res.wells()[:3]
    spr = reagent_res.wells()[3:11]
    water = reagent_res.wells()[11]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300)
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left',
                                tip_racks=tips1000)
    m300.flow_rate.aspirate = 150
    m300.flow_rate.dispense = 300
    m300.flow_rate.blow_out = 300
    p1000.flow_rate.aspirate = 100
    p1000.flow_rate.dispense = 1000
    p1000.flow_rate.blow_out = 1000

    tip_log = {'count': {}}
    folder_path = '/data/B'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips1000' in data:
                    tip_log['count'][p1000] = data['tips1000']
                else:
                    tip_log['count'][p1000] = 0
                if 'tips300' in data:
                    tip_log['count'][m300] = data['tips300']
                else:
                    tip_log['count'][m300] = 0
        else:
            tip_log['count'][m300] = 0
    else:
        tip_log['count'] = {p1000: 0, m300: 0}

    tip_log['tips'] = {
        p1000: [tip for rack in tips1000 for tip in rack.wells()],
        m300: [tip for rack in tips300 for tip in rack.rows()[0]]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [p1000, m300]
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

    def remove_supernatant(pip, vol):
        if pip == p1000:
            for i, s in enumerate(mag_samples_s):
                side = -1 if (i % 8) % 2 == 0 else 1
                loc = s.bottom(0.5).move(Point(x=side*2))
                pick_up(p1000)
                p1000.move_to(s.center())
                p1000.transfer(vol, loc, waste, new_tip='never', air_gap=100)
                p1000.blow_out(waste)
                p1000.drop_tip()

        else:
            m300.flow_rate.aspirate = 30
            for i, m in enumerate(mag_samples_m):
                side = -1 if i < 6 == 0 else 1
                loc = m.bottom(0.5).move(Point(x=side*2))
                if not m300.hw_pipette['has_tip']:
                    pick_up(m300)
                m300.move_to(m.center())
                m300.transfer(vol, loc, waste, new_tip='never', air_gap=20)
                m300.blow_out(waste)
                m300.drop_tip()
            m300.flow_rate.aspirate = 150

    # incubate on magnet
    magdeck.engage()
    ctx.delay(minutes=15, msg='Incubating on magnet for 15 minutes.')

    # remove supernatant with P1000
    remove_supernatant(p1000, 770)

    magdeck.disengage()

    # transfer and mix magnetic beads with VHB buffer
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        side = 1 if i % 2 == 0 else -1
        loc = m.bottom(0.5).move(Point(x=side*2))
        m300.transfer(400, vhb[i//4], m, new_tip='never')
        m300.mix(10, 200, loc)
        m300.blow_out(m.top(-2))
        m300.aspirate(20, m.top(-2))
        m300.drop_tip()

    # incubate on magnet
    magdeck.engage()
    ctx.delay(minutes=10, msg='Incubating on magnet for 10 minutes.')

    # remove supernatant with P300 multi
    remove_supernatant(m300, 420)

    # transfer and mix magnetic beads with SPR wash buffer 2x
    for wash in range(2):
        magdeck.disengage()
        for i, m in enumerate(mag_samples_m):
            pick_up(m300)
            col_ind = wash*num_cols+i
            wash_loc = spr[col_ind//3]
            side = 1 if i % 2 == 0 else -1
            loc = m.bottom(0.5).move(Point(x=side*2))
            m300.transfer(500, wash_loc, m, new_tip='never')
            m300.mix(10, 200, loc)
            m300.blow_out(m.top(-2))
            m300.aspirate(20, m.top(-2))
            m300.drop_tip()

        # incubate on magnet
        magdeck.engage()
        ctx.delay(minutes=10, msg='Incubating on magnet for 10 minutes.')

        # remove supernatant with P300 multi
        remove_supernatant(m300, 520)

    # transfer and mix water
    magdeck.disengage()
    for m in mag_samples_m:
        pick_up(m300)
        side = 1 if i % 2 == 0 else -1
        loc = m.bottom(0.5).move(Point(x=side*2))
        m300.transfer(ELUTION_VOL, water, m.top(), new_tip='never')
        m300.mix(10, 30, loc)
        m300.blow_out(m.top(-2))
        m300.drop_tip()

    # incubate off and on magnet
    ctx.delay(minutes=10, msg='Incubating off magnet for 10 minutes.')
    magdeck.engage()
    ctx.delay(minutes=10, msg='Incubating on magnet for 10 minutes.')

    # transfer elution to clean plate
    m300.flow_rate.aspirate = 30
    for s, d in zip(mag_samples_m, elution_samples_m):
        pick_up(m300)
        side = -1 if i % 2 == 0 else 1
        loc = s.bottom(0.5).move(Point(x=side*2))
        m300.transfer(ELUTION_VOL, loc, d, new_tip='never')
        m300.blow_out(d.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 150

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips1000': tip_log['count'][p1000],
            'tips300': tip_log['count'][m300]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
