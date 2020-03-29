metadata = {
    'protocolName': 'BP Genomics Station A 48 Samples',
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
    platewells = [well for pl in plate.columns()[::2] for well in pl]
    samplerack1 = protocol.load_labware('bpg_24_tuberack_2ml', '5')
    samplerack2 = protocol.load_labware('bpg_24_tuberack_2ml', '2')
    samps = samplerack1.wells()[:]+samplerack2.wells()[:]
    tempdeck = protocol.load_module('tempdeck', '7')
    temprack = tempdeck.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul')
    tempdeck.set_temperature(4)
    re_rack = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '4', 'Opentrons 24 TubeRack with Reagents')

    pk = re_rack['D6']
    lysis_wells = [
        re_rack[w] for w in [ltr+str(i) for ltr in 'ABCD' for i in range(1, 4)]
        ]
    spike1 = temprack['H1']
    spike2 = temprack['H4']

    p20.flow_rate.aspirate = 10
    p20.flow_rate.dispense = 20
    p20.flow_rate.blow_out = 100
    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300

    p300.pick_up_tip()
    lysis_tip = 2
    for idx, well in enumerate(platewells):
        l_well = idx//4
        if lysis_tip == l_well:
            p300.drop_tip()
            p300.pick_up_tip()
            lysis_tip += 2
        lysis = lysis_wells[l_well]
        for _ in range(2):
            p300.transfer(150, lysis, well.top(-2), new_tip='never')
    p300.drop_tip()

    p20.pick_up_tip()
    for well in platewells:
        p20.transfer(20, pk, well.top(-6), new_tip='never')
        p20.blow_out(well.top(-6))
    p20.drop_tip()

    p300.flow_rate.aspirate = 150
    p300.flow_rate.dispense = 300

    for src, dest in zip(samps, platewells):
        p300.pick_up_tip()
        p300.aspirate(180, src.bottom(9))
        for _ in range(2):
            p300.dispense(150, src.bottom(9))
            p300.aspirate(150, src.bottom(9))
        p300.dispense(180, src.bottom(9))
        p300.transfer(200, src.bottom(9), dest.top(-6), new_tip='never')
        p300.blow_out(dest.top(-6))
        p300.aspirate(200, src.bottom(9))
        for _ in range(5):
            p300.dispense(180, dest)
            p300.aspirate(180, dest)
        p300.dispense(200, dest)
        p300.blow_out(dest.top(-6))
        p300.aspirate(20, dest.top(-6))
        p300.drop_tip()

    for idx, well in enumerate(platewells):
        spike = spike1 if idx < 24 else spike2
        p20.pick_up_tip()
        p20.transfer(4, spike, well, new_tip='never')
        p20.drop_tip()
