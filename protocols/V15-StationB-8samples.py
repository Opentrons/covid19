from opentrons import types

metadata = {
    'protocolName': 'BP Genomics RNA Extraction',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}


def run(protocol):

    # load labware and pipettes
    tips200 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')

    p300 = protocol.load_instrument(
        'p300_multi_gen2', 'left')

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
    trough = protocol.load_labware(
                    'nest_12_reservoir_15ml', '2', 'Trough with Reagents')
    bind1 = trough['A3']
    wb1 = trough['A6']
    wb2 = trough['A8']
    ethanol1 = trough['A9']
    ethanol2 = trough['A10']
    water = trough['A12']

    magsamps = magplate['A1']
    elutes = flatplate['A1']

    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300

    def well_mix(reps, loc, vol):
        loc1 = loc.bottom().move(types.Point(x=1, y=0, z=0.5))
        loc2 = loc.bottom().move(types.Point(x=1, y=0, z=3.5))
        p300.aspirate(20, loc1)
        for _ in range(reps-1):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc2)

    p300.pick_up_tip(tips200['A1'])
    p300.aspirate(20, bind1.bottom(0.5))
    for _ in range(7):
        p300.aspirate(180, bind1.bottom(0.5))
        p300.dispense(180, bind1.bottom(2.5))
    p300.dispense(20, bind1)
    p300.blow_out(bind1.top())

    for _ in range(2):
        p300.transfer(
            210, bind1, magsamps.top(-3), new_tip='never')
        p300.blow_out(magsamps.top())
    well_mix(8, magsamps, 140)
    p300.blow_out(magsamps.top())

    protocol.comment('Incubating at room temp for 5 minutes. With mixing.')
    for _ in range(6):
        well_mix(12, magsamps, 120)
        p300.blow_out(magsamps.top(-10))
        protocol.delay(seconds=30)

    p300.drop_tip()
    protocol.delay(minutes=5)

    # Step 4 - engage magdeck for 6 minutes
    magdeck.engage(height=magheight)
    protocol.comment('Incubating on MagDeck for 7 minutes.')
    protocol.delay(minutes=7)

    # Step 5 - Remove supernatant
    def supernatant_removal(vol, src, dest):
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

    p300.pick_up_tip(tips200['A2'])
    supernatant_removal(1160, magsamps, waste2)
    p300.drop_tip()

    magdeck.disengage()

    def wash_step(src, mtimes, tips, wasteman):
        p300.pick_up_tip(tips200[tips])
        for _ in range(3):
            p300.transfer(200, src, magsamps.top(-3), new_tip='never')
        well_mix(mtimes, magsamps, 180)
        p300.blow_out(magsamps.top(-3))

        magdeck.engage(height=magheight)
        protocol.comment('Incubating on MagDeck for 6 minutes.')
        protocol.delay(minutes=6)

        # p300.pick_up_tip(tips200[tips])
        supernatant_removal(600, magsamps, wasteman)
        p300.drop_tip()
        magdeck.disengage()

    wash_step(wb1, 20, 'A3', waste2)

    wash_step(wb2, 10, 'A4', waste2)

    def eth_wash(src, tips, waste, keeptips):
        p300.pick_up_tip(tips200[tips])
        p300.flow_rate.aspirate = 50
        p300.flow_rate.dispense = 30
        for _ in range(3):
            p300.transfer(
                200, src,
                magsamps.top().move(types.Point(x=-1, y=0, z=-3)),
                new_tip='never')
        p300.blow_out(magsamps.top(-3))
        # p300.touch_tip()
        # p300.return_tip()

        # p300.pick_up_tip(tips200[tips])
        p300.flow_rate.aspirate = 30
        p300.flow_rate.dispense = 150
        for _ in range(3):
            p300.transfer(
                210, magsamps.bottom().move(types.Point(x=-1, y=0, z=0.5)),
                waste, new_tip='never')
        if not keeptips:
            p300.drop_tip()

    magdeck.engage(height=magheight)
    eth_wash(ethanol1, 'A5', waste2, False)

    eth_wash(ethanol2, 'A6', waste2, True)

    protocol.comment('Allowing beads to air dry for 2 minutes.')
    protocol.delay(minutes=2)

    p300.transfer(
        200, magsamps.bottom().move(types.Point(x=-0.4, y=0, z=0.3)),
        waste2, new_tip='never')
    p300.drop_tip()
    p300.flow_rate.aspirate = 50

    protocol.comment('Allowing beads to air dry for 10 minutes.')
    protocol.delay(minutes=10)

    magdeck.disengage()

    p300.pick_up_tip(tips200['A7'])
    p300.aspirate(30, water.top())
    p300.aspirate(30, water)
    for _ in range(15):
        p300.dispense(
            30, magsamps.bottom().move(types.Point(x=1, y=0, z=2)))
        p300.aspirate(
            30, magsamps.bottom().move(types.Point(x=1, y=0, z=0.5)))
    p300.dispense(30, magsamps)
    p300.dispense(30, magsamps.top())

    protocol.comment('Incubating at room temp for 2 minutes.')
    for i in range(5):
        p300.aspirate(20, magsamps.top(-4))
        p300.aspirate(30, magsamps)
        for _ in range(5):
            p300.dispense(
                20, magsamps.bottom().move(types.Point(x=1, y=0, z=2)))
            p300.aspirate(
                20, magsamps.bottom().move(types.Point(x=1, y=0, z=0.5)))
        p300.dispense(30, magsamps)
        p300.dispense(20, magsamps.top(-4))
        p300.blow_out(magsamps.top(-4))
        protocol.delay(seconds=45)

    # Step 21 - Transfer elutes to clean plate
    magdeck.engage(height=magheight)
    p300.drop_tip()
    protocol.comment('Incubating on MagDeck for 7 minutes.')
    protocol.delay(minutes=7)

    p300.flow_rate.aspirate = 10
    p300.pick_up_tip(tips200['A8'])
    p300.aspirate(20, magsamps.top())
    p300.aspirate(30, magsamps.bottom().move(types.Point(x=-1, y=0, z=0.8)))
    p300.dispense(50, elutes)
    p300.blow_out(elutes.top())
    p300.drop_tip()

    magdeck.disengage()

    protocol.comment('Congratulations!')
