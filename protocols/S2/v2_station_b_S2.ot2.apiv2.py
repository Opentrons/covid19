import math
from opentrons.types import Point
from opentrons import protocol_api
import os
import json

# metadata
metadata = {
    'protocolName': 'S2 Station B Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - beads and isopropanol: channels 1-2
    - 70% ethanol: channels 4-5
    - nuclease-free water: channel 12

"""

NUM_SAMPLES = 96
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    tempdeck = ctx.load_module('tempdeck', '1')
    elution_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul',
        'cooled elution plate')
    reagent_res = ctx.load_labware('nunc_96_wellplate_2000ul', '2',
                                   'reagent deepwell plate 1')
    # reagent_res = ctx.load_labware('usascientific_96_wellplate_2.4ml_deep',
    #                                '2')
    magdeck = ctx.load_module('magdeck', '4')
    magplate = magdeck.load_labware(
        'nunc_96_wellplate_2000ul', '96-deepwell sample plate')
    waste = ctx.load_labware(
        'nest_1_reservoir_195ml', '7', 'waste reservoir').wells()[0].top()
    tips300 = [
        ctx.load_labware(
            'opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
        for slot in ['3', '6', '8', '9', '10', '11']
    ]
    tips1000 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
        for slot in ['5']
    ]

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = [
        well for well in
        magplate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]
    mag_samples_s = [
        well for col in [
            c for set in [magplate.columns()[i::2] for i in range(2)]
            for c in set]
        for well in col][:NUM_SAMPLES]
    elution_samples_m = [
        well for well in
        elution_plate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]

    beads = reagent_res.rows()[0][:2]
    etoh = reagent_res.rows()[0][3:5]
    water = reagent_res.rows()[0][-1]

    # pipettes
    m300 = ctx.load_instrument('p300_multi', 'right', tip_racks=tips300)
    p1000 = ctx.load_instrument('p1000_single', 'left', tip_racks=tips1000)
    m300.flow_rate.aspirate = 150
    m300.flow_rate.dispense = 300
    m300.flow_rate.blow_out = 300
    p1000.flow_rate.aspirate = 100
    p1000.flow_rate.dispense = 1000

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
            tip_log['count'] = {p1000: 0, m300: 0}
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
                side = -1 if i < 48 == 0 else 1
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

    # premix, transfer, and mix magnetic beads with sample
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        if i == 0 or i == 6:
            for _ in range(20):
                m300.aspirate(200, beads[i//6].bottom(3))
                m300.dispense(200, beads[i//6].bottom(20))
        for _ in range(2):
            m300.transfer(310/2, beads[i//8], m.top(), new_tip='never')
        m300.mix(10, 200, m)
        m300.blow_out(m.top(-2))
        m300.aspirate(20, m.top(-2))
        m300.drop_tip()

    # incubate off and on magnet
    ctx.delay(minutes=5, msg='Incubating off magnet for 5 minutes.')
    magdeck.engage()
    ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes.')

    # remove supernatant
    remove_supernatant(p1000, 620)

    # 70% EtOH washes
    for wash in range(2):
        # transfer EtOH
        for m in mag_samples_m:
            side = -1 if i < 48 == 0 else 1
            loc = m.bottom(0.5).move(Point(x=side*2))
            pick_up(m300)
            m300.aspirate(200, etoh[wash])
            m300.aspirate(30, etoh[wash].top())
            m300.move_to(m.center())
            m300.dispense(30, m.center())
            m300.dispense(200, loc)
            m300.drop_tip()

        ctx.delay(seconds=30, msg='Incubating for 30 seconds.')

        # remove supernatant
        remove_supernatant(m300, 210)

    ctx.delay(minutes=5, msg='Airdrying beads for 5 minutes.')

    magdeck.disengage()

    # transfer and mix water
    for m in mag_samples_m:
        pick_up(m300)
        side = 1 if i < 6 == 0 else -1
        loc = m.bottom(0.5).move(Point(x=side*2))
        m300.transfer(50, water, m.center(), new_tip='never')
        m300.mix(10, 30, loc)
        m300.blow_out(m.top(-2))
        m300.drop_tip()

    # incubate off and on magnet
    ctx.delay(minutes=2, msg='Incubating on magnet for 2 minutes.')
    magdeck.engage()
    ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes.')

    # transfer elution to clean plate
    m300.flow_rate.aspirate = 30
    for s, d in zip(mag_samples_m, elution_samples_m):
        pick_up(m300)
        side = -1 if i < 6 == 0 else 1
        loc = s.bottom(0.5).move(Point(x=side*2))
        m300.transfer(45, loc, d, new_tip='never')
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
        with open(file_path, 'w') as outfile:
            json.dump(data, outfile)
