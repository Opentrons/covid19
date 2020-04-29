from opentrons import types

metadata = {
    'protocolName': 'Zymo Quick-DNA/RNA MagBead Station B 24 Samples',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Covid-19 Diagnostics',
    'apiLevel': '2.2'
}


def run(protocol):

    # load labware and pipettes
    tips_single = protocol.load_labware('opentrons_96_tiprack_300ul', '10')
    tr1 = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    tr2 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')
    tips20 = protocol.load_labware('opentrons_96_filtertiprack_20ul', '7')
    tips1 = [tr1['A'+str(i)] for i in range(1, 4)]
    tips2 = [tr1['A'+str(i)] for i in range(4, 7)]
    tips3 = [tr1['A'+str(i)] for i in range(7, 10)]
    tips4 = [tr1['A'+str(i)] for i in range(10, 13)]
    tips5 = [tr2['A'+str(i)] for i in range(1, 4)]
    tips6 = [tr2['A'+str(i)] for i in range(4, 7)]
    tips7 = [tr2['A'+str(i)] for i in range(7, 10)]
    tips8 = [tr2['A'+str(i)] for i in range(10, 13)]
    tips9 = [tips_single['A'+str(i)] for i in range(1, 4)]
    tips10 = [tips_single['A'+str(i)] for i in range(4, 7)]

    p300 = protocol.load_instrument(
        'p300_multi_gen2', 'left')

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'right', tip_racks=[tips20])

    magdeck = protocol.load_module('magdeck', '4')
    magheight = 13.7
    magplate = magdeck.load_labware('nest_96_deepwell_2ml')
    tempdeck = protocol.load_module('tempdeck', '3')
    tempdeck.set_temperature(6)
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '8', 'Opentrons 24 TubeRack')
    flatplate = tempdeck.load_labware(
                'opentrons_96_aluminumblock_nest_wellplate_100ul',)
    liqwaste2 = protocol.load_labware(
                'nest_1_reservoir_195ml', '11', 'Liquid Waste')
    waste2 = liqwaste2['A1'].top()
    trough = protocol.load_labware(
                    'nest_12_reservoir_15ml', '2', 'Trough with Reagents')
    buffer = [trough[xx] for xx in ['A1', 'A1', 'A2']]
    wb1 = trough['A4']
    wb2 = trough['A6']
    ethanol1 = trough['A8']
    ethanol2 = trough['A9']
    water = trough['A12']
    pk = tuberack['D1']
    iec = tuberack['D4']

    magsamps = [magplate['A'+str(i)] for i in range(1, 6, 2)]
    magsamps24 = [well for pl in magplate.columns()[:6:2] for well in pl]
    elutes = [flatplate['A'+str(i)] for i in range(1, 4)]

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

    # Add proteinase k
    protocol.comment('Adding Proteinase K to each well:')
    for well in magsamps24:
        p20.pick_up_tip()
        p20.aspirate(4, pk.bottom(0.5))
        p20.dispense(4, well)
        p20.blow_out()
        p20.drop_tip()

    # transfer 800ul of buffer
    protocol.comment('Adding viral buffer + beads to samples:')
    for well, reagent, tip in zip(magsamps, buffer, tips1):
        p300.pick_up_tip(tip)
        for _ in range(4):
            p300.aspirate(160, reagent)
            p300.dispense(160, well.top(-5))
            p300.aspirate(10, well.top(-5))
        p300.aspirate(160, reagent)
        p300.dispense(200, well.top(-10))
        well_mix(8, well, 180)
        p300.aspirate(20, well.top(-5))
        p300.drop_tip()

    # Add internal extraction control
    protocol.comment('Adding Internal Extraction Control to each well:')
    for well in magsamps24:
        p20.pick_up_tip()
        p20.aspirate(4, iec.bottom(0.5))
        p20.dispense(4, well)
        p20.blow_out()
        p20.drop_tip()

    # mix magbeads for 10 minutes
    protocol.comment('Mixing samples+buffer+beads:')
    for well, tip in zip(magsamps, tips2):
        p300.pick_up_tip(tip)
        well_mix(30, well, 180)
        p300.blow_out()
        p300.return_tip()

    magdeck.engage(height=magheight)
    protocol.comment('Incubating on magdeck for 5 minutes')
    protocol.delay(minutes=5)

    # Step 5 - Remove supernatant
    def supernatant_removal(vol, src, dest):
        p300.flow_rate.aspirate = 20
        tvol = vol
        while tvol > 180:
            p300.aspirate(
                180, src.bottom().move(types.Point(x=-1, y=0, z=0.5)))
            p300.dispense(180, dest)
            p300.aspirate(10, dest)
            tvol -= 180
        p300.aspirate(
            tvol, src.bottom().move(types.Point(x=-1, y=0, z=0.5)))
        p300.dispense(tvol+30, dest)
        p300.flow_rate.aspirate = 50

    protocol.comment('Removing supernatant:')

    for well, tip in zip(magsamps, tips2):
        p300.pick_up_tip(tip)
        supernatant_removal(520, well, waste2)
        p300.drop_tip()

    for well, tip in zip(magsamps, tips3):
        p300.pick_up_tip(tip)
        supernatant_removal(700, well, waste2)
        p300.drop_tip()

    magdeck.disengage()

    def wash_step(src, mtimes, tips, wasteman, trash_tips=True):
        for well, tip in zip(magsamps, tips):
            p300.pick_up_tip(tip)
            for _ in range(2):
                p300.aspirate(165, src)
                p300.dispense(165, well.top(-3))
                p300.aspirate(10, well.top(-3))
            p300.aspirate(165, src)
            p300.dispense(185, well.bottom(5))
            well_mix(mtimes, well, 180)
            p300.blow_out()
            p300.return_tip()

        magdeck.engage(height=magheight)
        protocol.comment('Incubating on MagDeck for 3 minutes.')
        protocol.delay(minutes=3)

        for well, tip in zip(magsamps, tips):
            p300.pick_up_tip(tip)
            supernatant_removal(495, well, wasteman)
            if trash_tips:
                p300.drop_tip()
            else:
                p300.return_tip()
        magdeck.disengage()

    protocol.comment('Wash step - Wash Buffer 1:')
    wash_step(wb1, 20, tips4, waste2)

    protocol.comment('Wash step - Wash Buffer 2:')
    wash_step(wb2, 10, tips5, waste2)

    protocol.comment('Wash step - Ethanol Wash 1:')
    wash_step(ethanol1, 10, tips6, waste2)

    protocol.comment('Wash step - Ethanol Wash 2:')
    wash_step(ethanol2, 10, tips7, waste2)

    protocol.comment('Allowing beads to air dry for 2 minutes.')
    protocol.delay(minutes=2)

    p300.flow_rate.aspirate = 20
    protocol.comment('Removing any excess ethanol from wells:')
    for well, tip in zip(magsamps, tips8):
        p300.pick_up_tip(tip)
        p300.transfer(
            180, well.bottom().move(types.Point(x=-0.5, y=0, z=0.4)),
            waste2, new_tip='never')
        p300.drop_tip()
    p300.flow_rate.aspirate = 50

    protocol.comment('Allowing beads to air dry for 10 minutes.')
    protocol.delay(minutes=10)

    magdeck.disengage()

    protocol.comment('Adding NF-Water to wells for elution:')
    for well, tip in zip(magsamps, tips9):
        p300.pick_up_tip(tip)
        p300.aspirate(20, water.top())
        p300.aspirate(50, water)
        for _ in range(15):
            p300.dispense(
                40, well.bottom().move(types.Point(x=1, y=0, z=2)))
            p300.aspirate(
                40, well.bottom().move(types.Point(x=1, y=0, z=0.5)))
        p300.dispense(70, well)
        p300.blow_out()
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
        p300.aspirate(50, src.bottom().move(types.Point(x=-0.8, y=0, z=0.6)))
        p300.dispense(50, dest)
        p300.drop_tip()

    magdeck.disengage()

    protocol.comment('Congratulations! Please freeze samples or move to C.')
