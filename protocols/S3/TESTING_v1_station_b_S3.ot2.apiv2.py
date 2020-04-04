import math
from opentrons.types import Point
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'TESTING S3 Station B Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - viral DNA/RNA buffer: channels 1-3
    - magbeads: channel 4
    - wash 1: channels 5-8
    - wash 2: channels 9-12

- slot 5 12-channel reservoir:
    - EtOH: channels 1-8
    - water: channel 12

"""

NUM_SAMPLES = 30


def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    tempdeck = ctx.load_module('tempdeck', '1')
    elution_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul',
        'cooled elution plate')
    reagent_res1 = ctx.load_labware(
        'nest_12_reservoir_15ml', '2', 'reagent reservoir 1')
    magdeck = ctx.load_module('magdeck', '4')
    magplate = magdeck.load_labware('usascientific_96_wellplate_2.4ml_deep')
    reagent_res2 = ctx.load_labware(
        'nest_12_reservoir_15ml', '5', 'reagent reservoir 2')
    waste = ctx.load_labware(
        'nest_1_reservoir_195ml', '7', 'waste reservoir').wells()[0].top()
    tips300 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul', slot, '300µl tiprack')
        for slot in ['3', '6', '8', '9', '10', '11']
    ]

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = [
        well for well in
        magplate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]
    elution_samples_m = [
        well for well in
        elution_plate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]

    viral_dna_rna_buff = reagent_res1.wells()[:3]
    beads = reagent_res1.wells()[3]
    wash_1 = reagent_res1.wells()[4:8]
    wash_2 = reagent_res1.wells()[8:]
    etoh = reagent_res2.wells()[:8]
    water = reagent_res2.wells()[-1]

    # pipettes
    m300 = ctx.load_instrument('p300_multi', 'left', tip_racks=tips300)
    m300.flow_rate.aspirate = 150
    m300.flow_rate.dispense = 300

    tip_counts = {m300: 0}
    tip_maxes = {m300: len(tips300)*12}

    def pick_up(pip):
        nonlocal tip_counts
        if tip_counts[pip] == tip_maxes[pip]:
            ctx.comment('Replace ' + str(pip.max_volume) + 'µl tipracks before \
    resuming.')
            pip.reset_tipracks()
            tip_counts[pip] = 0
        tip_counts[pip] += 1
        pip.pick_up_tip()

    def remove_supernatant(vol):
        m300.flow_rate.aspirate = 30
        num_trans = math.ceil(vol/270)
        vol_per_trans = vol/num_trans
        for i, m in enumerate(mag_samples_m):
            side = -1 if i < 6 == 0 else 1
            loc = m.bottom(0.5).move(Point(x=side*2))
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for _ in range(num_trans):
                m300.move_to(m.center())
                m300.transfer(vol_per_trans, loc, waste, new_tip='never',
                              air_gap=30)
                m300.blow_out(waste)
            m300.drop_tip()
        m300.flow_rate.aspirate = 150

    # transfer viral DNA/RNA buffer
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        m300.transfer(400, viral_dna_rna_buff[i//4], m.top(), new_tip='never')
        m300.mix(10, 200, m)
        m300.blow_out(m.top(-2))
        m300.drop_tip()

    # premix, transfer, and mix magnetic beads with sample
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)
        if i == 0:
            for _ in range(20):
                m300.aspirate(200, beads.bottom(3))
                m300.dispense(200, beads.bottom(20))
        m300.transfer(20, beads, m, new_tip='never')
        m300.mix(10, 200, m)
        m300.blow_out(m.top(-2))
        m300.drop_tip()

    # incubate on magnet
    magdeck.engage()
    ctx.comment('Incubating on magnet for 3 minutes.')

    # remove supernatant
    remove_supernatant(630)

    magdeck.disengage()

    for wash in [wash_1, wash_2]:
        # transfer and mix wash
        for i, m in enumerate(mag_samples_m):
            pick_up(m300)
            side = 1 if i < 6 == 0 else -1
            loc = m.bottom(0.5).move(Point(x=side*2))
            m300.transfer(500, wash[i//3], m.top(), new_tip='never')
            m300.mix(10, 200, loc)
            m300.blow_out(m.top(-2))
            m300.drop_tip()

        # incubate on magnet
        magdeck.engage()
        ctx.comment(minutes=3, msg='Incubating on magnet for 3 minutes.')

        # remove supernatant
        remove_supernatant(510)

        magdeck.disengage()

    # EtOH washes
    for wash in range(2):
        # transfer and mix wash
        etoh_set = etoh[wash*4:wash*4+4]
        pick_up(m300)
        m300.transfer(
            500, etoh_set[i//3], [m.top(3) for m in mag_samples_m],
            new_tip='never')
        ctx.comment(seconds=30, msg='Incubating in EtOH for 30 seconds.')

        # remove supernatant
        remove_supernatant(510)

        if wash == 1:
            ctx.comment(minutes=10, msg='Airdrying on magnet for 10 minutes.')

        magdeck.disengage()

    # transfer and mix water
    for m in mag_samples_m:
        pick_up(m300)
        side = 1 if i < 6 == 0 else -1
        loc = m.bottom(0.5).move(Point(x=side*2))
        m300.transfer(50, water, m.top(), new_tip='never')
        m300.mix(10, 30, loc)
        m300.blow_out(m.top(-2))
        m300.drop_tip()

    # incubate on magnet
    magdeck.engage()
    ctx.comment(minutes=3, msg='Incubating on magnet for 3 minutes.')

    # transfer elution to clean plate
    m300.flow_rate.aspirate = 30
    for s, d in zip(mag_samples_m, elution_samples_m):
        pick_up(m300)
        side = -1 if i < 6 == 0 else 1
        loc = s.bottom(0.5).move(Point(x=side*2))
        m300.transfer(50, loc, d, new_tip='never')
        m300.blow_out(d.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 150
