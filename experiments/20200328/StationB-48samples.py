from opentrons import types

metadata = {
    'protocolName': 'BP Genomics RNA Extraction',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}


def run(protocol):

    # load labware and pipettes
    tr1 = protocol.load_labware('opentrons_96_tiprack_300ul', '3')
    tr2 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')
    tr3 = protocol.load_labware('opentrons_96_tiprack_300ul', '9')
    tr4 = protocol.load_labware('opentrons_96_tiprack_300ul', '10')
    tips1 = [tr1['A'+str(i)] for i in range(1, 7)]
    tips2 = [tr1['A'+str(i)] for i in range(7, 13)]
    tips3 = [tr2['A'+str(i)] for i in range(1, 7)]
    tips4 = [tr2['A'+str(i)] for i in range(7, 13)]
    tips5 = [tr3['A'+str(i)] for i in range(1, 7)]
    tips6 = [tr3['A'+str(i)] for i in range(7, 13)]
    tips7 = [tr4['A'+str(i)] for i in range(1, 7)]
    tips8 = [tr4['A'+str(i)] for i in range(7, 13)]

    p300 = protocol.load_instrument(
        'p300_multi_gen2', 'left')

    magdeck = protocol.load_module('magdeck', '4')
    magheight = 13.7
    magplate = magdeck.load_labware('nest_96_deepwell_2ml')
    tempdeck = protocol.load_module('tempdeck', '1')
    flatplate = tempdeck.load_labware(
                'opentrons_96_aluminumblock_nest_wellplate_100ul',)
    liqwaste2 = protocol.load_labware(
                'nest_1_reservoir_195ml', '11', 'Liquid Waste')
    waste2 = liqwaste2['A1'].top()
    trough1 = protocol.load_labware(
                    'nest_12_reservoir_15ml', '2', 'Trough with Reagents')
    trough2 = protocol.load_labware(
                    'nest_12_reservoir_15ml', '5', 'Trough with Reagents')
    bind1 = trough2.wells()[:6]
    wb1 = [t for t in trough2.wells()[6:9] for _ in range(2)]
    wb2 = [t for t in trough2.wells()[9:] for _ in range(2)]
    ethanol1 = [t for t in trough1.wells()[:3] for _ in range(2)]
    ethanol2 = [t for t in trough1.wells()[3:6] for _ in range(2)]
    water = trough1['A12']

    magsamps = [magplate['A'+str(i)] for i in range(1, 13, 2)]
    elutes = [flatplate['A'+str(i)] for i in range(1, 7)]

    magdeck.disengage()  # just in case

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

    p300.pick_up_tip(tips1[0])
    for well, reagent in zip(magsamps, bind1):
        p300.transfer(
            210, reagent, well.top(-3), new_tip='never')
        p300.blow_out(well.top())

    for well, reagent in zip(magsamps, bind1):
        p300.aspirate(20, reagent.bottom(0.5))
        for _ in range(2):
            p300.aspirate(180, reagent.bottom(0.5))
            p300.dispense(180, reagent.bottom(2.5))
        p300.dispense(20, reagent)
        p300.transfer(
            210, reagent, well.top(-3), new_tip='never')
        p300.blow_out(well.top())

    for well, tip in zip(magsamps, tips1):
        if not p300.hw_pipette['has_tip']:
            p300.pick_up_tip(tip)
        well_mix(8, well, 140)
        p300.blow_out(well.top())
        p300.return_tip()

    protocol.comment('Incubating at room temp for 5 minutes. With mixing.')
    for _ in range(2):
        for well, tip in zip(magsamps, tips1):
            p300.pick_up_tip(tip)
            well_mix(15, well, 120)
            p300.blow_out(well.top(-10))
            p300.return_tip()

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
            tvol -= 200
        p300.transfer(
            tvol, src.bottom().move(types.Point(x=-1, y=0, z=0.5)),
            dest, new_tip='never')

    for well, tip in zip(magsamps, tips2):
        p300.pick_up_tip(tip)
        supernatant_removal(1160, well, waste2)
        p300.drop_tip()

    magdeck.disengage()

    def wash_step(src, mtimes, tips, wasteman):
        p300.pick_up_tip(tips[0])
        for well, s in zip(magsamps, src):
            for _ in range(3):
                p300.transfer(200, s, well.top(-3), new_tip='never')

        for well, tip in zip(magsamps, tips):
            if not p300.hw_pipette['has_tip']:
                p300.pick_up_tip(tip)
            well_mix(mtimes, well, 180)
            p300.blow_out(well.top(-3))
            p300.return_tip()

        magdeck.engage(height=magheight)
        protocol.comment('Incubating on MagDeck for 6 minutes.')
        protocol.delay(minutes=6)

        for well, tip in zip(magsamps, tips):
            p300.pick_up_tip(tip)
            supernatant_removal(600, well, wasteman)
            p300.drop_tip()

        magdeck.disengage()

    wash_step(wb1, 20, tips3, waste2)

    wash_step(wb2, 15, tips4, waste2)

    def eth_wash(src, tips, waste, keeptips):
        p300.pick_up_tip(tips[0])
        p300.flow_rate.aspirate = 50
        p300.flow_rate.dispense = 30
        for well, s in zip(magsamps, src):
            for _ in range(3):
                p300.transfer(
                    200, s,
                    well.top().move(types.Point(x=-1, y=0, z=-3)),
                    new_tip='never')
            p300.blow_out(well.top(-3))
        # p300.touch_tip()
        # p300.return_tip()

        # p300.pick_up_tip(tips200[tips])
        p300.flow_rate.aspirate = 30
        p300.flow_rate.dispense = 150
        for well, tip in zip(magsamps, tips):
            if not p300.hw_pipette['has_tip']:
                p300.pick_up_tip(tip)
            for _ in range(3):
                p300.transfer(
                    210, well.bottom().move(types.Point(x=-1, y=0, z=0.5)),
                    waste, new_tip='never')
            if not keeptips:
                p300.drop_tip()
            else:
                p300.return_tip()

    magdeck.engage(height=magheight)
    eth_wash(ethanol1, tips5, waste2, False)

    eth_wash(ethanol2, tips6, waste2, True)

    protocol.comment('Allowing beads to air dry for 2 minutes.')
    protocol.delay(minutes=2)

    for well, tip in zip(magsamps, tips6):
        p300.pick_up_tip(tip)
        p300.transfer(
            200, well.bottom().move(types.Point(x=-0.4, y=0, z=0.3)),
            waste2, new_tip='never')
        p300.drop_tip()
    p300.flow_rate.aspirate = 50

    protocol.comment('Allowing beads to air dry for 10 minutes.')
    protocol.delay(minutes=10)
    tempdeck.set_temperature(4)

    magdeck.disengage()

    for well, tip in zip(magsamps, tips7):
        p300.pick_up_tip(tip)
        p300.aspirate(30, water.top())
        p300.aspirate(30, water)
        for _ in range(10):
            p300.dispense(
                30, well.bottom().move(types.Point(x=1, y=0, z=2)))
            p300.aspirate(
                30, well.bottom().move(types.Point(x=1, y=0, z=0.5)))
        p300.dispense(30, well)
        p300.dispense(30, well.top())
        p300.return_tip()

    protocol.comment('Incubating at room temp for 2 minutes.')
    for well, tip in zip(magsamps, tips7):
        p300.pick_up_tip(tip)
        p300.aspirate(20, well.top(-4))
        p300.aspirate(30, well)
        for _ in range(5):
            p300.dispense(
                20, well.bottom().move(types.Point(x=1, y=0, z=2)))
            p300.aspirate(
                20, well.bottom().move(types.Point(x=1, y=0, z=0.5)))
        p300.dispense(30, well)
        p300.dispense(20, well.top(-4))
        p300.blow_out(well.top(-4))
        p300.drop_tip()

    # Step 21 - Transfer elutes to clean plate
    magdeck.engage(height=magheight)
    protocol.comment('Incubating on MagDeck for 5 minutes.')
    protocol.delay(minutes=5)

    p300.flow_rate.aspirate = 10
    for src, dest, tip in zip(magsamps, elutes, tips8):
        p300.pick_up_tip(tip)
        p300.aspirate(20, src.top())
        p300.aspirate(30, src.bottom().move(types.Point(x=-1, y=0, z=0.8)))
        p300.dispense(50, dest)
        p300.blow_out(dest.top())
        p300.drop_tip()

    magdeck.disengage()

    protocol.comment('Congratulations!')
