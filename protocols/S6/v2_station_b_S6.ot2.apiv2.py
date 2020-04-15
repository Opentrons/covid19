import math
from opentrons.types import Point
from opentrons import protocol_api
from opentrons.protocol_api.labware import OutOfTipsError

# metadata
metadata = {
    'protocolName': 'S2 Station B Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - enzyme mix: channel 1
    - binding bead mix: channels 3-8
    - water: channel 12

"""

NUM_SAMPLES = 16


def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    tempdeck = ctx.load_module('tempdeck', '1')
    elution_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul',
        'cooled elution plate')
    reagent_res = ctx.load_labware(
        'nest_12_reservoir_15ml', '2', 'reagent reservoir 1')
    magdeck = ctx.load_module('magdeck', '4')
    magplate = magdeck.load_labware('nest_96_deepwell_2ml')
    magdeck.disengage()
    etoh = ctx.load_labware(
        'nest_1_reservoir_195ml', '5', 'reservoir for ethanol').wells()[0]
    waste = ctx.load_labware(
        'nest_1_reservoir_195ml', '7', 'waste reservoir').wells()[0].top()
    wash_buffer = ctx.load_labware(
        'nest_1_reservoir_195ml', '8', 'reservoir for wash buffer').wells()[0]

    if NUM_SAMPLES < 16:
        tuberack = ctx.load_labware('opentrons_24_tuberack_generic_2ml_screwcap', '10')
        tips300 = [
            ctx.load_labware(
                'opentrons_96_filtertiprack_200ul', slot, '200µl filter tiprack')
            for slot in ['3', '6', '9', '11']]
    else:
        tips300 = [
            ctx.load_labware(
                'opentrons_96_filtertiprack_200ul', slot, '200µl filter tiprack')
            for slot in ['3', '6', '9', '10', '11']]

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = [well for well in magplate.rows()[0]][:num_cols]
    elution_samples_m = [well for well in elution_plate.rows()[0]][:num_cols]

    if NUM_SAMPLES < 16:
        enzyme_mix = tuberack.wells()[0]
    else:
        enzyme_mix = reagent_res.wells()[0]
    beads = reagent_res.wells()[2:8]
    water = reagent_res.wells()[-1]

    # pipettes
    if NUM_SAMPLES < 16:
        p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300)
    aspirate_flow_rate = m300.flow_rate.aspirate
    dispense_flow_rate = m300.flow_rate.dispense
    working_volume = min(m300.max_volume, m300.tip_racks[0]['A1'].max_volume)

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except OutOfTipsError:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before '
                      'resuming.')
            pip.reset_tipracks()
            pick_up(pip)

    def remove_supernatant(vol):
        m300.flow_rate.aspirate = aspirate_flow_rate * 4/5
        transfer_vol = working_volume - m300.min_volume
        num_trans = math.ceil(vol/transfer_vol)
        for i, m in enumerate(mag_samples_m):
            side = -1 if i % 2 == 0 else 1
            print(side)
            loc = m.bottom(0.5).move(Point(x=side*1))
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for _ in range(num_trans):
                m300.move_to(m.center())
                m300.aspirate(transfer_vol, loc)
                m300.air_gap()
                m300.dispense(location=waste)
                m300.blow_out()
            m300.drop_tip()
        m300.flow_rate.aspirate = aspirate_flow_rate

    # transfer enzyme mix
    pip = p300 if NUM_SAMPLES < 16 else m300
    for m in mag_samples_m:
        pick_up(pip)
        pip.aspirate(50, enzyme_mix)
        pip.dispense(50, m)
        pip.blow_out(m.top(-15))
        pip.aspirate(20, m.top())
        pip.drop_tip()

    # premix, transfer, and mix magnetic beads with sample
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        if i % 2 == 0:
            # resuspend beads by mixing each column 20 times at 200 µL slowly
            m300.flow_rate.aspirate = aspirate_flow_rate * 5/6
            m300.flow_rate.dispense = dispense_flow_rate * 5/6            
            for j in range(20):
                m300.aspirate(200, beads[i//2].bottom(3))
                m300.dispense(200, beads[i//2].bottom(20))
                if j == 19:
                    m300.blow_out()
            m300.flow_rate.aspirate = aspirate_flow_rate
            m300.flow_rate.dispense = dispense_flow_rate
        # transfer 550 µL beads to each sample
        for vol in [200, 75]:
            for i in range(2):
                m300.aspirate(vol, beads[i//2])
                m300.dispense(vol, m.top(-15))
                m300.blow_out(m.top(-15))
        m300.mix(10, 200, m)
        m300.blow_out(m.top(-15))
        m300.aspirate(20, m.top(-15))
        m300.drop_tip()

    ctx.pause('Incubate the sealed plate at 65°C for 5 minutes')

    # mix the samples again
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        side = 1 if i % 2 == 0 else -1
        print(side)
        loc = m.bottom(1).move(Point(x=side*0.5))
        m300.move_to(m.center())
        m300.mix(10, 200, loc)
        m300.blow_out(m.top(-15))
        m300.aspirate(20, m.top(-15))
        m300.drop_tip()

    # incubate on magnet
    magdeck.engage()
    ctx.delay(minutes=10, msg='Incubating on magnet for 10 minutes.')

    # remove supernatant
    remove_supernatant(810)

    for vol, wash_reagent in zip([1000, 1000, 500], [wash_buffer, etoh, etoh]):

        magdeck.disengage()

        # transfer and mix wash
        num_trans = math.ceil(vol/working_volume)
        vol_per_trans = vol/num_trans
        for i, m in enumerate(mag_samples_m):
            pick_up(m300)
            side = 1 if i % 2 == 0 else -1
            print(side)
            loc = m.bottom(1).move(Point(x=side*0.5))
            for _ in range(num_trans):
                m300.aspirate(vol_per_trans, wash_reagent)
                m300.dispense(vol_per_trans, m.top(-10))
                m300.blow_out()
            m300.move_to(m.center())
            m300.mix(10, 200, loc)
            m300.blow_out(m.top(-15))
            m300.aspirate(20, m.top(-15))
            m300.drop_tip()

        # incubate on magnet
        magdeck.engage()
        ctx.delay(minutes=2, msg='Incubating on magnet for 2 minutes.')

        # remove supernatant
        remove_supernatant(vol+10)

    ctx.delay(minutes=2, msg="Airdrying beads for 2 minutes.")

    # transfer and mix water for elution
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        side = 1 if i % 2 == 0 else -1
        print(side)
        loc = m.bottom(1).move(Point(x=side*0.5))
        m300.aspirate(50, water)
        m300.dispense(50, m)
        m300.mix(10, 30, loc)
        m300.blow_out(m.bottom(5))
        m300.aspirate(20, m.bottom(5))
        m300.drop_tip()

    ctx.pause('Incubate the sealed plate at 65°C for 10 minutes.')

    # resuspend beads again
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        side = 1 if i % 2 == 0 else -1
        print(side)
        loc = m.bottom(1).move(Point(x=side*0.5))
        m300.move_to(m.center())
        m300.mix(10, 30, loc)
        m300.blow_out(m.bottom(5))
        m300.aspirate(20, m.bottom(5))
        m300.drop_tip()

    # incubate on magnet
    magdeck.engage()
    ctx.delay(minutes=3, msg='Incubating on magnet for 3 minutes.')

    # transfer elution to clean plate
    m300.flow_rate.aspirate = aspirate_flow_rate * 5/6
    for i, (s, d) in enumerate(zip(mag_samples_m, elution_samples_m)):
        pick_up(m300)
        side = -1 if i % 2 == 0 else 1
        print(side)
        loc = s.bottom(1).move(Point(x=side*0.5))
        m300.aspirate(50, loc)
        m300.dispense(50, d)
        m300.blow_out(d.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = aspirate_flow_rate
