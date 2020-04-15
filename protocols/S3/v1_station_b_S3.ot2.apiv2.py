import math
from opentrons.types import Point
from opentrons import protocol_api
import os
import json

# metadata
metadata = {
    'protocolName': 'S3 Station B Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 7 12-channel reservoir:
    - elution buffer: channel 1
    - magnetic beads: channel 2
    - bead buffer: channels 3-5
    - wash 1: channels 6-7
    - wash 2: channels 8-9
    - wash 3: channels 10-11

- slot 11 single-channel reservoir:
    - empty reservoir for liquid waste (supernatant removals)

"""

NUM_SAMPLES = 96
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    tempdeck = ctx.load_module('tempdeck', '1')
    elution_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul',
        'cooled elution plate')
    magdeck = ctx.load_module('magdeck', '10')
    magdeck.disengage()
    magplate = magdeck.load_labware('usascientific_96_wellplate_2.4ml_deep')
    waste = ctx.load_labware(
        'nest_1_reservoir_195ml', '11', 'waste reservoir').wells()[0].top()
    reagent_res = ctx.load_labware(
        'nest_12_reservoir_15ml', '7', 'reagent reservoir')
    tips300 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul', slot, '200µl filter tiprack')
        for slot in ['2', '3', '5', '6', '9']
    ]
    tips1000 = [
        ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot,
                         '1000µl filter tiprack')
        for slot in ['4', '8']
    ]

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = magplate.rows()[0][:num_cols]
    mag_samples_s = magplate.wells()[:NUM_SAMPLES]
    elution_samples_m = elution_plate.rows()[0][:num_cols]

    elution_buffer = reagent_res.wells()[0]
    beads = reagent_res.wells()[1]
    bead_buffer = reagent_res.wells()[2:5]
    wash_sets = [reagent_res.wells()[i:i+2] for i in [5, 7, 9]]

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
    file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(file_path):
            with open(file_path) as json_file:
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

    # mix beads and add to buffer
    bead_dests = bead_buffer[:math.ceil(num_cols/4)]
    pick_up(m300)
    m300.mix(5, 200, beads)
    m300.transfer(200, beads, bead_dests, new_tip='never')

    # premix, transfer, and mix magnetic beads with sample
    for d in bead_dests:
        for _ in range(5):
            m300.aspirate(200, d.bottom(3))
            m300.dispense(200, d.bottom(20))

    for i, m in enumerate(mag_samples_m):
        if not m300.hw_pipette['has_tip']:
            pick_up(m300)
        m300.transfer(400, bead_buffer[i//4], m, new_tip='never')
        m300.mix(5, 200, m)
        m300.blow_out(m.top(-2))
        m300.drop_tip()

    # incubate off and on magnet
    ctx.delay(minutes=5, msg='Incubating off magnet for 5 minutes.')
    magdeck.engage()
    ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes.')

    # remove supernatant with P1000
    for i, m in enumerate(mag_samples_s):
        side = -1 if (i % 8) % 2 == 0 else 1
        loc = m.bottom(0.5).move(Point(x=side*2))
        pick_up(p1000)
        p1000.move_to(m.center())
        p1000.transfer(900, loc, waste, air_gap=100, new_tip='never')
        p1000.blow_out(waste)
        p1000.drop_tip()

    # 3x washes
    for wash_set in wash_sets:
        for i, m in enumerate(mag_samples_m):
            # transfer and mix wash with beads
            magdeck.disengage()
            wash_chan = wash_set[i//6]
            side = 1 if i % 2 == 0 else -1
            disp_loc = m.bottom(0.5).move(Point(x=side*2))
            asp_loc = m.bottom(0.5).move(Point(x=-1*side*2))
            pick_up(m300)
            m300.transfer(200, wash_chan, m.center(), new_tip='never')
            m300.mix(5, 175, disp_loc)
            m300.move_to(m.top(-20))

            magdeck.engage()
            ctx.delay(seconds=20, msg='Incubating on magnet for 20 seconds.')

            # remove supernatant
            m300.transfer(200, asp_loc, waste, new_tip='never', air_gap=20)
            m300.drop_tip()

    ctx.delay(minutes=5, msg='Airdrying for 5 minutes.')

    # elute samples
    for i, (m, e) in enumerate(zip(mag_samples_m, elution_samples_m)):
        # tranfser and mix elution buffer with beads
        magdeck.disengage()
        side = 1 if i % 2 == 0 else -1
        disp_loc = m.bottom(0.5).move(Point(x=side*2))
        asp_loc = m.bottom(0.5).move(Point(x=-1*side*2))
        pick_up(m300)
        m300.transfer(50, elution_buffer, m.center(), new_tip='never')
        m300.mix(5, 40, disp_loc)
        m300.move_to(m.top(-20))

        magdeck.engage()
        ctx.delay(seconds=30, msg='Incubating on magnet for 30 seconds.')

        # transfer elution to new plate
        m300.transfer(50, asp_loc, e, new_tip='never', air_gap=20)
        m300.drop_tip()

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips1000': tip_log['count'][p1000],
            'tips300': tip_log['count'][m300]
        }
        with open(file_path, 'w') as outfile:
            json.dump(data, outfile)
