from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S2 Station C Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 5 2ml tuberack:
    - mastermixes: tube A1
    - positive control: tube B1
    - negative control: tube B2
"""

NUM_SAMPLES = 8
VOLUME_MMIX = 20


def run(ctx: protocol_api.ProtocolContext):
    source_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '1',
        'chilled RNA elution plate from station B')
    tempdeck = ctx.load_module('tempdeck', '4')
    pcr_plate = tempdeck.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', 'PCR plate')
    tempdeck.set_temperature(4)
    tuberack = ctx.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap', '7',
        'chilled 2ml screw tube block for mastermix')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['2', '5', '8']
    ]

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)

    # setup up sample sources and destinations
    samples = source_plate.wells()[:NUM_SAMPLES]
    dests = pcr_plate.wells()[:NUM_SAMPLES]
    mm = tuberack.rows()[0]

    # ensure volume does not reach the filter of the tip
    max_trans_per_asp = 230//(VOLUME_MMIX+5)  # max tip volume of 230µl

    # split destination wells into sets that can be distributed to with 1 aspiration
    split_ind = [ind for ind in range(0, NUM_SAMPLES, max_trans_per_asp)]
    dest_sets = [dests[split_ind[i]:split_ind[i+1]]
                 for i in range(len(split_ind)-1)] + [dests[split_ind[-1]:]]

    # distribute to each set of wells using the same tip for each
    p20.pick_up_tip()
    for set in dest_sets:
        p20.distribute(VOLUME_MMIX, mm, [d.bottom(2) for d in set],
                       air_gap=5, disposal_volume=0, new_tip='never')
    p20.drop_tip()

    # transfer samples to corresponding locations
    for s, d in zip(samples, dests):
        p20.pick_up_tip()
        p20.transfer(5, s, d, new_tip='never')
        p20.mix(1, 10, d)
        p20.aspirate(5, d.top(2))
        p20.drop_tip()
