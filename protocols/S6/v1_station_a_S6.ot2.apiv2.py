from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S6 Station A Version 1.1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 8
SAMPLE_VOLUME = 300
ENZYME_VOLUME = 50
PK_VOLUME = 10

""" REAGENT SETUP

For samples Less Than or Equal To 16:
    2ml screwcap tuberack in slot 5:
    - Enzyme Mix in Tube A1
    - Proteinase K in Tube B1

For samples Greater Than 16:
    2ml screwcap tuberack in slot 5
    - Proteinase K in Tube B1

    12 Channel Reservoir:
    - Enzyme Mix in Column 1
"""


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    source_racks = [
        ctx.load_labware(
            'mhs_24_tuberack_2ml', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['1', '3', '4', '6'])
    ]
    dest_plate = ctx.load_labware(
        'nest_96_deepwell_2ml', '2',
        '96-deepwell sample plate')
    tuberack = ctx.load_labware(
        'mhs_24_tuberack_2ml', '5')
    tiprack20 = ctx.load_labware(
        'opentrons_96_filtertiprack_20ul', '10', '20µl filter tiprack')
    tiprack2_200 = ctx.load_labware(
        'opentrons_96_filtertiprack_200ul', '11', '200µl filter tiprack')
    tiprack1_200 = ctx.load_labware(
        'opentrons_96_filtertiprack_200ul', '8', '200µl filter tiprack')

    # load pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack20])
    p300 = ctx.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack1_200, tiprack2_200])
    pk = tuberack['B1']

    if NUM_SAMPLES <= 16:
        enzyme_mix = tuberack['A1']
    else:
        reservoir = ctx.load_labware('nest_12_reservoir_15ml', '7')
        enzyme_mix = reservoir['A1']


    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests = [well for col in dest_plate.columns()[0::2] for well in col] + [
        well for col in dest_plate.columns()[1::2] for well in col]
    dests = dests[:NUM_SAMPLES]

    # transfer sample
    for s, d in zip(sources, dests):
        p300.pick_up_tip()
        p300.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p300.aspirate(100, d.top())
        p300.drop_tip()

    # transfer enzyme mix
    p300.pick_up_tip()
    for m in dests:
        p300.aspirate(ENZYME_VOLUME, enzyme_mix.bottom(0.25))
        p300.dispense(ENZYME_VOLUME, m.top(-10))
        p300.blow_out(m.top(-15))
        p300.air_gap(20)
    p300.drop_tip()

    ctx.pause('Shake the sealed plate at 1,050 rpm for 5 minutes, then incubate\n'
              'for 15 minutes at 65°C. Shake the sealed plate at 1,050\n'
              'rpm for 5 minutes.')

    # transfer internal control
    p20.transfer(PK_VOLUME, pk, [d.bottom(5) for d in dests], air_gap=5,
                 new_tip='always')
