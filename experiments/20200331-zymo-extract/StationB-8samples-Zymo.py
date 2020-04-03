from opentrons import types

metadata = {
    'protocolName': 'Zymo Quick-DNA/RNA MagBead Station B',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}


def run(protocol):

    # load labware and pipettes
    tips200 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')

    p300 = protocol.load_instrument(
        'p300_multi_gen2', 'left')

    p300_single = protocol.load_instrument('p300_single_gen2', 'right')

    magdeck = protocol.load_module('magdeck', '4')
    magheight = 13.7
    magplate = magdeck.load_labware('nest_96_deepwell_2ml')
    tempdeck = protocol.load_module('tempdeck', '1')
    tempdeck.set_temperature(4)
    flatplate = tempdeck.load_labware(
                'opentrons_96_aluminumblock_nest_wellplate_100ul',)
    liqwaste2 = protocol.load_labware(
                'nest_1_reservoir_195ml', '11', 'Liquid Waste')
    waste2 = liqwaste2['A1'].top()
    reagentrack = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '5', 'Opentrons 24 TubeRack with Reagents')
    trough = protocol.load_labware(
                    'nest_12_reservoir_15ml', '2', 'Trough with Reagents')
    magbeads = reagentrack['A1']
    buffer = trough['A1']
    wb1 = trough['A3']
    wb2 = trough['A5']
    ethanol1 = trough['A7']
    ethanol2 = trough['A8']
    water = trough['A12']

    magsamps = magplate['A1']
    magsamps_single = magplate.wells()[:8]
    elutes = flatplate['A1']

    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300

    def well_mix(reps, loc, vol):
        loc1 = loc.bottom().move(types.Point(x=1, y=0, z=0.5))
        loc2 = loc.bottom().move(types.Point(x=1, y=0, z=5.5))
        p300.aspirate(20, loc1)
        for _ in range(reps-1):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc2)

    # transfer 800ul of buffer
    p300.pick_up_tip(tips200['A1'])
    for _ in range(4):
        p300.transfer(200, buffer, magsamps.top(-5), new_tip='never')
    well_mix(10, magsamps, 180)
    p300.blow_out(magsamps.top(-5))
    p300.drop_tip()

    # Transfer magbeads
    p300_single.pick_up_tip(tips200['H11'])
    p300_single.aspirate(150, magbeads)
    for _ in range(20):
        p300_single.dispense(130, magbeads)
        p300_single.aspirate(130, magbeads)
    p300_single.dispense(130, magbeads)
    p300_single.blow_out(magbeads.top())

    for well in magsamps_single:
        p300_single.transfer(20, magbeads, well.top(-3), new_tip='never')
        p300_single.blow_out(well.top(-3))
    p300_single.drop_tip()

    # mix magbeads for 10 minutes
    p300.pick_up_tip(tips200['A2'])
    for _ in range(10):
        well_mix(20, magsamps, 180)
        p300.move_to(magsamps.top(-5))
        protocol.delay(seconds=30)

    p300.drop_tip()

    magdeck.engage(height=magheight)
    protocol.comment('Incubating on magdeck for 5 minutes')
    protocol.delay(minutes=5)

    # Step 5 - Remove supernatant
    def supernatant_removal(vol, src, dest):
        p300.flow_rate.aspirate = 20
        tvol = vol
        while tvol > 200:
            p300.aspirate(20, src.top())
            p300.aspirate(
                200, src.bottom().move(types.Point(x=-1, y=0, z=0.5)))
            p300.dispense(220, dest)
            # p300.blow_out(dest)
            tvol -= 200
        p300.transfer(
            tvol, src.bottom().move(types.Point(x=-1, y=0, z=0.5)),
            dest, new_tip='never')
        p300.flow_rate.aspirate = 50

    p300.pick_up_tip(tips200['A3'])
    supernatant_removal(1223, magsamps, waste2)
    p300.drop_tip()

    magdeck.disengage()

    def wash_step(src, mtimes, tips, wasteman, trash_tips=True):
        p300.pick_up_tip(tips200[tips])
        for _ in range(3):
            p300.transfer(165, src, magsamps.top(-3), new_tip='never')
        well_mix(mtimes, magsamps, 180)
        p300.blow_out(magsamps.top(-3))

        magdeck.engage(height=magheight)
        protocol.comment('Incubating on MagDeck for 3 minutes.')
        protocol.delay(minutes=3)

        # p300.pick_up_tip(tips200[tips])
        supernatant_removal(495, magsamps, wasteman)
        if trash_tips:
            p300.drop_tip()
        magdeck.disengage()

    wash_step(wb1, 15, 'A4', waste2)

    wash_step(wb2, 10, 'A5', waste2)

    wash_step(ethanol1, 10, 'A6', waste2)

    wash_step(ethanol2, 10, 'A7', waste2, False)

    protocol.comment('Allowing beads to air dry for 2 minutes.')
    protocol.delay(minutes=2)

    p300.flow_rate.aspirate = 20
    p300.transfer(
        200, magsamps.bottom().move(types.Point(x=-0.4, y=0, z=0.3)),
        waste2, new_tip='never')
    p300.drop_tip()
    p300.flow_rate.aspirate = 50

    protocol.comment('Allowing beads to air dry for 10 minutes.')
    protocol.delay(minutes=10)

    magdeck.disengage()

    p300.pick_up_tip(tips200['A8'])
    p300.aspirate(30, water.top())
    p300.aspirate(30, water)
    for _ in range(15):
        p300.dispense(
            30, magsamps.bottom().move(types.Point(x=1, y=0, z=2)))
        p300.aspirate(
            30, magsamps.bottom().move(types.Point(x=1, y=0, z=0.5)))
    p300.dispense(30, magsamps)
    p300.dispense(30, magsamps.top(-5))
    p300.blow_out(magsamps.top(-4))

    protocol.comment('Incubating at room temp for 2 minutes.')
    protocol.delay(minutes=2)

    # Step 21 - Transfer elutes to clean plate
    magdeck.engage(height=magheight)
    p300.drop_tip()
    protocol.comment('Incubating on MagDeck for 4 minutes.')
    protocol.delay(minutes=4)

    p300.flow_rate.aspirate = 10
    p300.pick_up_tip(tips200['A9'])
    p300.aspirate(20, magsamps.top())
    p300.aspirate(30, magsamps.bottom().move(types.Point(x=-0.7, y=0, z=0.7)))
    p300.dispense(50, elutes)
    p300.blow_out(elutes.top())
    p300.drop_tip()

    magdeck.disengage()

    protocol.comment('Congratulations!')
