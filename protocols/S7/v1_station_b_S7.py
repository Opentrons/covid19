from opentrons import types
import json
import os
import math

metadata = {
    'protocolName': 'V1 S7 Station B (BP Genomics RNA Extraction)',
    'author': 'Nick <ndiehl@opentrons.com',
    'apiLevel': '2.2'
}

NUM_SAMPLES = 48
TIP_TRACK = False


def run(ctx):

    # load labware and pipettes
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
               for slot in ['3', '6', '9', '10']]

    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'left', tip_racks=tips300)

    magdeck = ctx.load_module('magdeck', '4')
    magheight = 13.7
    magplate = magdeck.load_labware('biorad_96_wellplate_200ul_pcr')
    tempdeck = ctx.load_module('tempdeck', '1')
    flatplate = tempdeck.load_labware(
                'opentrons_96_aluminumblock_nest_wellplate_100ul',)
    liqwaste2 = ctx.load_labware(
                'nest_1_reservoir_195ml', '11', 'Liquid Waste')
    waste2 = liqwaste2['A1'].top()
    trough1 = ctx.load_labware(
                    'nest_1_reservoir_195ml', '2', 'Trough with Ethanol')
    trough2 = ctx.load_labware(
                    'nest_12_reservoir_15ml', '5', 'Trough with Reagents')
    bind1 = trough2.wells()[:6]
    wb1 = [t for t in trough2.wells()[6:9] for _ in range(2)]
    wb2 = trough1['A1']
    ethanol1 = trough1['A1']
    ethanol2 = trough1['A1']
    water = trough2['A12']

    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = [
        well for set in [magplate.rows()[0][i::2] for i in range(2)]
        for well in set
    ][:num_cols]
    elution_samples_m = [
        well for set in [flatplate.rows()[0][i::2] for i in range(2)]
        for well in set
    ][:num_cols]

    magdeck.disengage()  # just in case
    tempdeck.set_temperature(4)

    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 300

    folder_path = '/data/B'
    tip_file_path = folder_path + '/tip_log.json'
    tip_log = {'count': {}}
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips300' in data:
                    tip_log['count'][m300] = data['tips300']
                else:
                    tip_log['count'][m300] = 0
        else:
            tip_log['count'][m300] = 0
    else:
        tip_log['count'] = {m300: 0}

    tip_log['tips'] = {
        m300: [tip for rack in tips300 for tip in rack.rows()[0]]}
    tip_log['max'] = {m300: len(tip_log['tips'][m300])}

    def pick_up(pip, loc=None):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        if loc:
            pip.pick_up_tip(loc)
        else:
            pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
            tip_log['count'][pip] += 1

    def well_mix(reps, loc, vol):
        loc1 = loc.bottom().move(types.Point(x=1, y=0, z=0.5))
        loc2 = loc.bottom().move(types.Point(x=1, y=0, z=3.5))
        m300.aspirate(20, loc1)
        for _ in range(reps-1):
            m300.aspirate(vol, loc1)
            m300.dispense(vol, loc2)
        m300.dispense(20, loc2)

    pick_up(m300)
    for well, reagent in zip(mag_samples_m, bind1):
        m300.transfer(
            210, reagent, well.top(-3), new_tip='never')
        m300.blow_out(well.top())

    for well, reagent in zip(mag_samples_m, bind1):
        m300.aspirate(20, reagent.bottom(0.5))
        for _ in range(2):
            m300.aspirate(180, reagent.bottom(0.5))
            m300.dispense(180, reagent.bottom(2.5))
        m300.dispense(20, reagent)
        m300.transfer(
            210, reagent, well.top(-3), new_tip='never')
        m300.blow_out(well.top())

    tip_block = []
    for well in mag_samples_m:
        if not m300.hw_pipette['has_tip']:
            pick_up(m300)
        tip_block.append(m300._last_tip_picked_up_from)
        well_mix(8, well, 140)
        m300.blow_out(well.top())
        m300.return_tip()

    ctx.comment('Incubating at room temp for 5 minutes. With mixing.')
    for _ in range(2):
        for well, tip in zip(mag_samples_m, tip_block):
            pick_up(m300, tip)
            well_mix(15, well, 120)
            m300.blow_out(well.top(-10))
            m300.return_tip()

    # Step 4 - engage magdeck for 7 minutes
    magdeck.engage(height=magheight)
    ctx.delay(minutes=7, msg='Incubating on MagDeck for 7 minutes.')

    # Step 5 - Remove supernatant
    def supernatant_removal(vol, src, dest):
        tvol = vol
        m300.flow_rate.aspirate = 25
        while tvol > 200:
            m300.aspirate(20, src.top())
            m300.aspirate(
                200, src.bottom().move(types.Point(x=-1, y=0, z=0.5)))
            m300.dispense(220, dest)
            tvol -= 200
        m300.transfer(
            tvol, src.bottom().move(types.Point(x=-1, y=0, z=0.5)),
            dest, new_tip='never')
        m300.flow_rate.aspirate = 50

    for well in mag_samples_m:
        pick_up(m300)
        supernatant_removal(1160, well, waste2)
        m300.drop_tip()

    magdeck.disengage()

    def wash_step(src, mtimes, wasteman):
        pick_up(m300)
        if src == wb1:
            for well, s in zip(mag_samples_m, src):
                for _ in range(3):
                    m300.transfer(200, s, well.top(-3), new_tip='never')
        else:
            for well in mag_samples_m:
                for _ in range(3):
                    m300.transfer(200, src, well.top(-3), new_tip='never')

        wash_tip_block = []
        for well in mag_samples_m:
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            wash_tip_block.append(m300._last_tip_picked_up_from)
            well_mix(mtimes, well, 180)
            m300.blow_out(well.top(-3))
            m300.return_tip()

        magdeck.engage(height=magheight)
        ctx.delay(minutes=6, msg='Incubating on MagDeck for 6 minutes.')

        for well, tip in zip(mag_samples_m, wash_tip_block):
            pick_up(m300, tip)
            supernatant_removal(600, well, wasteman)
            m300.drop_tip()

        magdeck.disengage()

    wash_step(wb1, 20, waste2)

    wash_step(wb2, 15, waste2)

    def eth_wash(src, waste, keeptips):
        pick_up(m300)
        m300.flow_rate.aspirate = 50
        m300.flow_rate.dispense = 30
        for well in mag_samples_m:
            for _ in range(3):
                m300.transfer(
                    200, src,
                    well.top().move(types.Point(x=-1, y=0, z=-3)),
                    new_tip='never')
            m300.blow_out(well.top(-3))
        # m300.touch_tip()
        # m300.return_tip()

        # pick_up(m300, tips200[tips])
        m300.flow_rate.aspirate = 30
        m300.flow_rate.dispense = 150
        for well in mag_samples_m:
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for _ in range(3):
                m300.transfer(
                    210, well.bottom().move(types.Point(x=-1, y=0, z=0.5)),
                    waste, new_tip='never')
            if not keeptips:
                m300.drop_tip()
            else:
                m300.return_tip()

    magdeck.engage(height=magheight)
    eth_wash(ethanol1, waste2, False)

    eth_wash(ethanol2, waste2, False)

    ctx.comment('Allowing beads to air dry for 2 minutes.')
    ctx.delay(minutes=2)

    # for well, tip in zip(mag_samples_m, tips6):
    #     pick_up(m300, tip)
    #     m300.transfer(
    #         200, well.bottom().move(types.Point(x=-0.4, y=0, z=0.3)),
    #         waste2, new_tip='never')
    #     m300.drop_tip()
    m300.flow_rate.aspirate = 50

    ctx.delay(minutes=10, msg='Allowing beads to air dry for 10 minutes.')

    magdeck.disengage()

    pick_up(m300)
    for well in mag_samples_m:
        m300.aspirate(30, water.top())
        m300.aspirate(30, water)
        m300.dispense(60, well.top(-5))
        m300.blow_out(well.top(-3))

    for well in mag_samples_m:
        if not m300.hw_pipette['has_tip']:
            pick_up(m300)
        for _ in range(12):
            m300.dispense(
                30, well.bottom().move(types.Point(x=1, y=0, z=2)))
            m300.aspirate(
                30, well.bottom().move(types.Point(x=1, y=0, z=0.5)))
        m300.dispense(30, well)
        m300.dispense(30, well.top(-4))
        m300.blow_out(well.top(-4))
        m300.drop_tip()

    ctx.delay(minutes=2, msg='Incubating at room temp for 2 minutes.')

    # Step 21 - Transfer elution_samples_m to clean plate
    magdeck.engage(height=magheight)
    ctx.comment('Incubating on MagDeck for 5 minutes.')
    ctx.delay(minutes=5)

    m300.flow_rate.aspirate = 10
    for src, dest in zip(mag_samples_m, elution_samples_m):
        pick_up(m300)
        m300.aspirate(20, src.top())
        m300.aspirate(30, src.bottom().move(types.Point(x=-0.8, y=0, z=0.6)))
        m300.dispense(50, dest)
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    magdeck.disengage()
