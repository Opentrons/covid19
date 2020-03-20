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
    """liqwaste1 = protocol.load_labware(
                'nest_1_reservoir_195ml', '10', 'Liquid Waste')
    waste1 = liqwaste1['A1'].top()"""
    liqwaste2 = protocol.load_labware(
                'nest_1_reservoir_195ml', '11', 'Liquid Waste')
    waste2 = liqwaste2['A1'].top()
    trough = protocol.load_labware(
                    'nest_12_reservoir_15ml', '2', 'Trough with Reagents')
    bind1 = trough['A2']
    wb1 = trough['A6']
    wb2 = trough['A8']
    ethanol1 = trough['A9']
    ethanol2 = trough['A10']
    water = trough['A12']

    magsamps = magplate['A1']
    elutes = flatplate['A1']

    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 50
    p300.flow_rate.dispense = 300

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

    """bind = [trough['A1'], trough['A1'], trough['A1'], trough['A2'],
            trough['A2'], trough['A2'], trough['A3'], trough['A3'],
            trough['A3'], trough['A4'], trough['A4'], trough['A4']]

    washb1 = [trough2['A1'], trough2['A1'], trough2['A2'], trough2['A2'],
              trough2['A3'], trough2['A3'], trough2['A4'], trough2['A4'],
              trough2['A5'], trough2['A5'], trough2['A6'], trough2['A6']]

    washb2 = [trough2['A7'], trough2['A7'], trough2['A8'], trough2['A8'],
              trough2['A9'], trough2['A9'], trough2['A10'], trough2['A10'],
              trough2['A11'], trough2['A11'], trough2['A12'], trough2['A12']]

    ethlist = [trough['A5'], trough['A5'], trough['A6'], trough['A6'],
               trough['A7'], trough['A7'], trough['A8'], trough['A8'],
               trough['A9'], trough['A9'], trough['A10'], trough['A10']]"""

    """for dest, tr, b in zip(magsamps, tiprange, bind):
        if not p300.hw_pipette['has_tip']:
            p300.pick_up_tip(tips200[0][tr])
        p300.transfer(200, b, dest.top(), new_tip='never')
        p300.transfer(200, b, dest.top(), new_tip='never')
        p300.transfer(180, b, dest.top(), new_tip='never')
        well_mix(5, dest)
        p300.blow_out(dest.top())
        p300.return_tip()"""
    p300.flow_rate.aspirate = 50
    for _ in range(2):
        p300.transfer(
            210, bind1, magsamps.top(-3), new_tip='never')
        p300.blow_out(magsamps.top())
    well_mix(8, magsamps, 140)
    p300.blow_out(magsamps.top())

    protocol.comment('Incubating at room temp for 5 minutes. With mixing.')
    for _ in range(8):
        well_mix(12, magsamps, 120)
        p300.blow_out(magsamps.top(-10))
        protocol.delay(seconds=30)

    p300.drop_tip()
    protocol.delay(minutes=5)

    # Step 4 - engage magdeck for 6 minutes
    magdeck.engage(height=magheight)
    protocol.comment('Incubating on MagDeck for 6 minutes.')
    protocol.delay(minutes=6)

    # Step 5 - Remove supernatant
    def supernatant_removal(vol, src, dest):
        tvol = vol
        while tvol > 200:
            p300.aspirate(20, src.top())
            p300.aspirate(
                200, src.bottom().move(types.Point(x=-1, y=0, z=1)))
            p300.dispense(220, dest)
            # p300.blow_out(dest)
            tvol -= 200
        p300.transfer(
            tvol, src.bottom().move(types.Point(x=-1, y=0, z=1)),
            dest, new_tip='never')

    """for src, tr in zip(magsamps, tiprange):
        p300.pick_up_tip(tips200[0][tr])
        supernatant_removal(980, src, waste2)
        p300.drop_tip()"""

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
        # p300.touch_tip()
        # p300.return_tip()

        magdeck.engage(height=magheight)
        protocol.comment('Incubating on MagDeck for 7 minutes.')
        protocol.delay(minutes=7)

        # p300.pick_up_tip(tips200[tips])
        supernatant_removal(600, magsamps, wasteman)
        p300.drop_tip()
        magdeck.disengage()

    wash_step(wb1, 10, 'A3', waste2)

    wash_step(wb2, 5, 'A4', waste2)

    def eth_wash(src, tips, waste, keeptips):
        p300.pick_up_tip(tips200[tips])
        for _ in range(3):
            p300.transfer(200, src, magsamps.top(-3), new_tip='never')
        p300.blow_out(magsamps.top(-3))
        # p300.touch_tip()
        # p300.return_tip()

        # p300.pick_up_tip(tips200[tips])
        for _ in range(3):
            p300.transfer(
                210, magsamps.bottom().move(types.Point(x=-1, y=0, z=1)),
                waste, new_tip='never')
        if not keeptips:
            p300.drop_tip()

    magdeck.engage(height=magheight)
    eth_wash(ethanol1, 'A5', waste2, False)

    eth_wash(ethanol2, 'A6', waste2, True)

    protocol.comment('Allowing beads to air dry for 2 minutes.')
    protocol.delay(minutes=2)

    # p300.pick_up_tip(tips200['A5'])
    p300.flow_rate.aspirate = 20
    # protocol.pause('check for liquid')
    p300.transfer(
        100, magsamps.bottom().move(types.Point(x=-1, y=0, z=1)),
        waste2, new_tip='never')
    p300.drop_tip()
    p300.flow_rate.aspirate = 50

    protocol.comment('Allowing beads to air dry for 10 minutes.')
    protocol.delay(minutes=10)

    magdeck.disengage()

    # Remove any residual liquid
    """for src, tr in zip(magsamps, tiprange):
        p300.pick_up_tip(tips200[3][tr])
        p300.transfer(100, src, waste2, new_tip='never')
        p300.drop_tip()"""

    """p300.pick_up_tip(tips200['A5'])
    p300.transfer(100, magsamps, waste1, new_tip='never')
    p300.drop_tip()"""

    # Step 20 - Add 40ul of nuclease free water and incubate for 2 minutes
    """for dest, tr in zip(magsamps, tiprange):
        p300.pick_up_tip(tips200[4][tr])
        p300.aspirate(20, water.top())
        p300.aspirate(40, water)
        for _ in range(7):
            p300.dispense(40, dest)
            p300.aspirate(40, water)
        p300.dispense(40, dest)
        p300.dispense(20, dest.top())
        p300.return_tip()"""

    p300.pick_up_tip(tips200['A7'])
    p300.aspirate(30, water.top())
    p300.aspirate(30, water)
    for _ in range(7):
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

    """for src, dest, tr in zip(magsamps, elutes, tiprange):
        p300.pick_up_tip(tips200[4][tr])
        p300.transfer(40, src, dest, new_tip='never')
        p300.blow_out(dest.top())
        p300.drop_tip()"""

    p300.flow_rate.aspirate = 10
    p300.pick_up_tip(tips200['A8'])
    p300.aspirate(20, magsamps.top())
    p300.aspirate(30, magsamps.bottom().move(types.Point(x=-1, y=0, z=1)))
    p300.dispense(50, elutes)
    p300.blow_out(elutes.top())
    p300.drop_tip()

    magdeck.disengage()

    protocol.comment('Congratulations!')
