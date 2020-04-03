metadata = {
    'protocolName': 'Zymo Quick-DNA/RNA MagBead Station A',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}


def run(protocol):
    tips200 = [protocol.load_labware('opentrons_96_tiprack_300ul', '9')]
    tips20 = [protocol.load_labware('opentrons_96_filtertiprack_20ul', '8')]
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'left', tip_racks=tips200)
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'right', tip_racks=tips20)
    plate = protocol.load_labware('nest_96_deepwell_2ml', '1')
    platewells = plate.wells()[:8]
    samplerack = protocol.load_labware('bpg_24_tuberack_2ml', '2')
    samps = samplerack.wells()[:8]
    reagentrack = protocol.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul',
        '4', 'Opentrons 96 Al Block with Reagents')

    pk = reagentrack['H12']
    spike1 = reagentrack['H1']

    p20.flow_rate.aspirate = 10
    p20.flow_rate.dispense = 20
    p20.flow_rate.blow_out = 100
    p300.flow_rate.aspirate = 150
    p300.flow_rate.dispense = 300
    p300.flow_rate.blow_out = 300

    for src, dest in zip(samps, platewells):
        p300.pick_up_tip()
        p300.aspirate(180, src.bottom(9))
        for _ in range(2):
            p300.dispense(150, src.bottom(9))
            p300.aspirate(150, src.bottom(9))
        p300.dispense(180, src.bottom(9))
        p300.transfer(200, src.bottom(9), dest, new_tip='never')
        p300.blow_out(dest.top(-6))
        p300.transfer(200, src.bottom(9), dest, new_tip='never')
        p300.blow_out(dest.top(-6))
        p300.drop_tip()

    for well in platewells:
        p20.pick_up_tip()
        p20.transfer(4, spike1, well, new_tip='never')
        p20.drop_tip()

    for well in platewells:
        p20.pick_up_tip()
        p20.aspirate(4, pk)
        p20.dispense(3, well)
        for _ in range(3):
            p20.aspirate(15, well)
            p20.dispense(15, well)
        p20.dispense(1, well)
        p20.blow_out(well.top(-3))
        p20.drop_tip()
