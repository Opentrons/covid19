from opentrons import types

metadata = {
    'protocolName': 'Zymo Quick-DNA/RNA MagBead Station B 48 Samples',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Covid-19 Diagnostics',
    'apiLevel': '2.2'
}


def run(protocol):

    # load labware and pipettes
    tr1 = protocol.load_labware('opentrons_96_tiprack_300ul', '3')
    tr2 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')
    tr3 = protocol.load_labware('opentrons_96_tiprack_300ul', '9')
    tr4 = protocol.load_labware('opentrons_96_tiprack_300ul', '7')
    tr5 = protocol.load_labware('opentrons_96_tiprack_300ul', '10')
    tips1 = [tr1['A'+str(i)] for i in range(1, 7)]
    tips2 = [tr1['A'+str(i)] for i in range(7, 13)]
    tips3 = [tr2['A'+str(i)] for i in range(1, 7)]
    tips4 = [tr2['A'+str(i)] for i in range(7, 13)]
    tips5 = [tr3['A'+str(i)] for i in range(1, 7)]
    tips6 = [tr3['A'+str(i)] for i in range(7, 13)]
    tips7 = [tr4['A'+str(i)] for i in range(1, 7)]
    tips8 = [tr4['A'+str(i)] for i in range(7, 13)]
    tips9 = [tr5['A'+str(i)] for i in range(1, 7)]
    tips10 = [tr5['A'+str(i)] for i in range(7, 13)]

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
    buffer = [trough[xx] for xx in ['A1', 'A1', 'A2', 'A2', 'A3', 'A3']]
    wb1 = [trough[xx] for xx in ['A4', 'A5'] for _ in range(3)]
    wb2 = [trough[xx] for xx in ['A6', 'A7'] for _ in range(3)]
    ethanol1 = [trough[xx] for xx in ['A8', 'A9'] for _ in range(3)]
    ethanol2 = [trough[xx] for xx in ['A10', 'A11'] for _ in range(3)]
    water = trough['A12']

    magsamps = [magplate['A'+str(i)] for i in range(1, 12, 2)]
    elutes = [flatplate['A'+str(i)] for i in range(1, 7)]

    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300

    def well_mix(reps, loc, vol):
        loc1 = loc.bottom().move(types.Point(x=1, y=0, z=0.6))
        loc2 = loc.bottom().move(types.Point(x=1, y=0, z=5.5))
        p300.aspirate(20, loc1)
        for _ in range(reps-1):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc2)

    # transfer 800ul of buffer
    protocol.comment('Adding viral buffer + beads to samples:')
    for well, reagent, tip in zip(magsamps, buffer, tips1):
        p300.pick_up_tip(tip)
        for _ in range(5):
            p300.transfer(160, reagent, well.top(-5), new_tip='never')
        well_mix(8, well, 180)
        p300.move_to(well.top(-5))
        protocol.delay(seconds=2)
        p300.blow_out(well.top(-5))
        p300.drop_tip()

    # mix magbeads for 10 minutes
    protocol.comment('Mixing samples+buffer+beads:')
    for well, tip in zip(magsamps, tips2):
        p300.pick_up_tip(tip)
        well_mix(30, well, 180)
        p300.move_to(well.top(-5))
        protocol.delay(seconds=3)
        p300.blow_out(well.top(-5))
        p300.return_tip()

    magdeck.engage(height=magheight)
    protocol.comment('Incubating on magdeck for 5 minutes')
    protocol.delay(minutes=5)

    # Step 5 - Remove supernatant
    def supernatant_removal(vol, src, dest):
        p300.flow_rate.aspirate = 20
        tvol = vol
        while tvol > 180:
            p300.aspirate(20, src.top())
            p300.aspirate(
                180, src.bottom().move(types.Point(x=-1, y=0, z=0.5)))
            p300.dispense(200, dest)
            protocol.delay(seconds=2)
            p300.blow_out(dest)
            tvol -= 180
        p300.transfer(
            tvol, src.bottom().move(types.Point(x=-1, y=0, z=0.5)),
            dest, new_tip='never')
        protocol.delay(seconds=2)
        p300.blow_out(dest)
        p300.flow_rate.aspirate = 50

    for well, tip in zip(magsamps, tips3):
        p300.pick_up_tip(tip)
        supernatant_removal(1225, well, waste2)
        p300.drop_tip()

    magdeck.disengage()

    def wash_step(src, mtimes, tips, wasteman, msg):
        protocol.comment(f'Wash Step {msg} - Adding to samples:')
        for well, tip, s in zip(magsamps, tips, src):
            p300.pick_up_tip(tip)
            for _ in range(3):
                p300.transfer(165, s, well.top(-3), new_tip='never')
            well_mix(mtimes, well, 180)
            p300.move_to(well.top(-3))
            protocol.delay(seconds=2)
            p300.blow_out(well.top(-3))
            p300.return_tip()

        magdeck.engage(height=magheight)
        protocol.comment('Incubating on MagDeck for 3 minutes.')
        protocol.delay(minutes=3)

        protocol.comment(f'Removing supernatant from Wash {msg}:')
        for well, tip in zip(magsamps, tips):
            p300.pick_up_tip(tip)
            supernatant_removal(495, well, wasteman)
            p300.return_tip()
        magdeck.disengage()

    wash_step(wb1, 20, tips4, waste2, '1 Wash Buffer 1')

    wash_step(wb2, 10, tips5, waste2, '2 Wash Buffer 2')

    wash_step(ethanol1, 10, tips6, waste2, '3 Ethanol 1')

    wash_step(ethanol2, 10, tips7, waste2, '4 Ethanol 2')

    protocol.comment('Allowing beads to air dry for 2 minutes.')
    protocol.delay(minutes=2)

    p300.flow_rate.aspirate = 20
    protocol.comment('Removing any excess ethanol from wells:')
    for well, tip in zip(magsamps, tips8):
        p300.pick_up_tip(tip)
        p300.transfer(
            180, well.bottom().move(types.Point(x=-0.5, y=0, z=0.4)),
            waste2, new_tip='never')
        p300.return_tip()
    p300.flow_rate.aspirate = 50

    protocol.comment('Allowing beads to air dry for 10 minutes.')
    protocol.delay(minutes=10)

    magdeck.disengage()

    protocol.comment('Adding NF-Water to wells for elution:')
    for well, tip in zip(magsamps, tips9):
        p300.pick_up_tip(tip)
        p300.aspirate(30, water.top())
        p300.aspirate(50, water)
        for _ in range(15):
            p300.dispense(
                30, well.bottom().move(types.Point(x=1, y=0, z=2)))
            p300.aspirate(
                30, well.bottom().move(types.Point(x=1, y=0, z=0.5)))
        p300.dispense(50, well)
        p300.dispense(30, well.top(-5))
        protocol.delay(seconds=2)
        p300.blow_out(well.top(-4))
        p300.drop_tip()

    protocol.comment('Incubating at room temp for 2 minutes.')
    protocol.delay(minutes=2)

    # Step 21 - Transfer elutes to clean plate
    magdeck.engage(height=magheight)
    protocol.comment('Incubating on MagDeck for 4 minutes.')
    protocol.delay(minutes=4)

    protocol.comment('Transferring elution to final plate:')
    p300.flow_rate.aspirate = 10
    for src, dest, tip in zip(magsamps, elutes, tips10):
        p300.pick_up_tip(tip)
        p300.aspirate(20, src.top())
        p300.aspirate(50, src.bottom().move(types.Point(x=-0.7, y=0, z=0.7)))
        p300.dispense(70, dest)
        p300.blow_out(dest.top())
        p300.drop_tip()

    magdeck.disengage()

    protocol.comment('Congratulations!')
