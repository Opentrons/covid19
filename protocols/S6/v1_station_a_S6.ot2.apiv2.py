from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S6 Station A Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

NUM_SAMPLES = 48
SAMPLE_VOLUME = 300

""" REAGENT SETUP

2ml screwcap tuberack in slot 5:
- Proteinase K: tube A1

"""


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['1', '3', '4', '6'])
    ]
    dest_plate = ctx.load_labware(
        'nest_96_deepwell_2ml', '2',
        '96-deepwell sample plate')
    prot_k = ctx.load_labware(
        'opentrons_24_tuberack_generic_2ml_screwcap', '5').wells()[0]
    tiprack20 = ctx.load_labware(
        'opentrons_96_filtertiprack_1000ul', '10', '20µl filter tiprack')
    tiprack1000 = ctx.load_labware(
        'opentrons_96_filtertiprack_1000ul', '11', '1000µl filter tiprack')

    # load pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack20])
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=[tiprack1000])

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests = [well for col in dest_plate.columns()[0::2] for well in col] + [
        well for col in dest_plate.columns()[1::2] for well in col]
    dests = dests[:NUM_SAMPLES]

    # transfer sample
    for s, d in zip(sources, dests):
        p1000.pick_up_tip()
        p1000.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p1000.aspirate(100, d.top())
        p1000.drop_tip()

    # transfer internal control
    p20.transfer(10, prot_k, [d.bottom(5) for d in dests], air_gap=5,
                 new_tip='always')

    ctx.comment('Move deepwell plate (slot 5) to Station B for RNA \
extraction.')
