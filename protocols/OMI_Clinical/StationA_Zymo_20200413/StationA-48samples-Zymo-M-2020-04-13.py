metadata = {
    'protocolName': 'Zymo Quick-DNA/RNA MagBead Station A 24 Samples',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Covid-19 Diagnostics',
    'apiLevel': '2.2'
}


def run(protocol):
    tips200 = [protocol.load_labware('opentrons_96_tiprack_300ul', '6')]
    tips20 = [protocol.load_labware('opentrons_96_filtertiprack_20ul', '3')]
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'left', tip_racks=tips200)
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'right', tip_racks=tips20)
    plate = protocol.load_labware('nest_96_deepwell_2ml', '1')
    platewells = [well for pl in plate.columns()[:12:2] for well in pl]
    reagentrack = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '7', 'Opentrons 24 TubeRack')

    pk = reagentrack['D1']
    spike1 = reagentrack['D4']

    p20.flow_rate.aspirate = 10
    p20.flow_rate.dispense = 20
    p20.flow_rate.blow_out = 100
    p300.flow_rate.aspirate = 150
    p300.flow_rate.dispense = 300
    p300.flow_rate.blow_out = 300

    p20.pick_up_tip()
    for well in platewells:
        p20.transfer(4, pk, well, new_tip='never')
        p20.blow_out(well.bottom(5))
    p20.drop_tip()

    p20.pick_up_tip()
    for well in platewells:
        p20.transfer(4, spike1, well.bottom(6), new_tip='never')
        p20.blow_out(well.top(-6))
    p20.drop_tip()
