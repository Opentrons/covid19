metadata = {
    'protocolName': 'BP Genomics Station A',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}


def run(protocol):
    tips200 = [protocol.load_labware('opentrons_96_tiprack_300ul', '8')]
    tips20 = [protocol.load_labware('opentrons_96_filtertiprack_20ul', '7')]
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'left', tip_racks=tips200)
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'right', tip_racks=tips20)
    tempdeck = protocol.load_module('tempdeck', '4')
    temprack = tempdeck.load_labware(
        'opentrons_24_aluminumblock_nest_0.5ml_screwcap')
    plate = protocol.load_labware('nest_96_deepwell_2ml', '1')
    platewells = plate.wells()[:8]
    tr = protocol.load_labware('bpg_24_tuberack_2ml', '5')
    samps = tr.wells()[:8]
    tempdeck.set_temperature(4)

    spike = temprack['A1']
    pk = temprack['A3']
    lysis = temprack['A5']

    for well in samps:
        p20.pick_up_tip()
        p20.transfer(20, pk, well.top(-2), new_tip='never')
        p20.drop_tip()

    for well in samps:
        p300.pick_up_tip()
        for _ in range(2):
            p300.transfer(150, lysis, well.top(-1), new_tip='never')
        p300.mix(10, 200, well.bottom(4))
        p300.blow_out(well.top(-1))
        p300.drop_tip()

    protocol.comment('Incubating for 25 minutes. Screw PK and Lysis Buffer')
    protocol.delay(minutes=25)

    for src, dest in zip(samps, platewells):
        p300.pick_up_tip()
        for _ in range(4):
            p300.transfer(180, src.bottom(4), dest, new_tip='never')
        p300.blow_out(dest.top(-1))
        p300.drop_tip()

    protocol.pause('Unscrew Spike')

    for well in platewells:
        p20.pick_up_tip()
        p20.transfer(4, spike, well, new_tip='never')
        p20.drop_tip()
