from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S5 Station C Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.1'
}

"""
MM_TYPE must be one of the following:
    Seegene
    singleplex
"""

NUM_SAMPLES = 94
PREPARE_MASTERMIX = True
MM_TYPE = 'singleplex'


def run(ctx: protocol_api.ProtocolContext):
    global MM_TYPE

    # check source (elution) labware type
    source_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul', '1',
        'chilled elution plate on block from Station B')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3', '6', '9']
    ]
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '2')]
    tempdeck = ctx.load_module('tempdeck', '4')
    pcr_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul', 'PCR plate')
    tempdeck.set_temperature(4)
    tube_block = ctx.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap', '5',
        '2ml screw tube aluminum block for mastermix + controls')

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)

    # setup up sample sources and destinations
    sources = source_plate.wells()[:NUM_SAMPLES]

    """ mastermix component maps """
    # component setup
    components = {
        'nCov MOM': tube_block.wells_by_name()['A2'],
        'Rnase-free H20': tube_block.wells_by_name()['B2'],
        '5x real time one-step buffer': tube_block.wells_by_name()['C2'],
        'real time one-step enzyme': tube_block.wells_by_name()['D2'],
        'Rxn buffer 5x': tube_block.wells_by_name()['A3'],
        'dNTPs mix': tube_block.wells_by_name()['B3'],
        'Primer F': tube_block.wells_by_name()['C3'],
        'Primer R': tube_block.wells_by_name()['D3'],
        'Enzyme Mix': tube_block.wells_by_name()['A4'],
        'H20': tube_block.wells_by_name()['B4'],
        'E gene sonda/probe': tube_block.wells_by_name()['C4'],
        'RNasP gene sonda/probe': tube_block.wells_by_name()['D4']
    }

    MM_TYPE = MM_TYPE.lower().strip()
    mm_tube = tube_block.wells()[0]
    # for Seegene
    mm1 = {
        'location': tube_block.wells_by_name()['A1'],
        'volume': 17,
        'components': {
            components[tube]: vol
            for tube, vol in zip(
                ['nCov MOM', 'Rnase-free H20', '5x real time one-step buffer',
                 'real time one-step enzyme'],
                [5, 5, 5, 2])
        }
    }

    # for other 3x masetermixes
    mm2 = {
        'location': tube_block.wells_by_name()['A1'],
        'volume': 20,
        'components': {
            components[tube]: vol
            for tube, vol in zip(
                ['Rxn buffer 5x', 'dNTPs mix', 'Primer F', 'Primer R',
                 'Enzyme Mix', 'H20', 'E gene sonda/probe'],
                [5, 1, 2, 2, 1, 8, 1])
        }
    }
    mm3 = {
        'location': tube_block.wells_by_name()['B1'],
        'volume': 20,
        'components': {
            components[tube]: vol
            for tube, vol in zip(
                ['Rxn buffer 5x', 'dNTPs mix', 'Primer F', 'Primer R',
                 'Enzyme Mix', 'H20'],
                [5, 1, 2, 2, 1, 9])
        }
    }
    mm4 = {
        'location': tube_block.wells_by_name()['C1'],
        'volume': 20,
        'components': {
            components[tube]: vol
            for tube, vol in zip(
                ['Rxn buffer 5x', 'dNTPs mix', 'Primer F', 'Primer R',
                 'Enzyme Mix', 'H20', 'RNasP gene sonda/probe'],
                [5, 1, 2, 2, 1, 8, 1])
        }
    }

    mm_dict = {
        'seegene': [mm1],
        'singleplex': [mm2, mm3, mm4]
    }

    if PREPARE_MASTERMIX:
        # create mastermix
        for mm, tube_dest in zip(mm_dict[MM_TYPE], tube_block.rows()[0]):
            for r_tube, vol in mm['components'].items():
                mm_vol = vol*NUM_SAMPLES*1.1
                disp_loc = tube_dest.bottom(5) if mm_vol < 50 \
                    else tube_dest.top(-5)
                pip = p300 if mm_vol > 20 else p20
                pip.transfer(
                    mm_vol, r_tube.bottom(2), disp_loc, new_tip='once')

    if MM_TYPE == 'seegene':
        sample_dests = pcr_plate.wells()[:NUM_SAMPLES]
        mm_dests = sample_dests + pcr_plate.wells()[-2:]

        # transfer mastermix
        mm_vol = mm_dict[MM_TYPE][0]['volume']

        p20.pick_up_tip()
        for d in mm_dests:
            p20.transfer(mm_vol, mm_tube, d.bottom(2), new_tip='never')
            p20.blow_out(d.bottom(5))
        p20.drop_tip()

        # transfer samples to corresponding locations
        sample_vol = 25 - mm_vol
        for s, d in zip(sources, sample_dests):
            p20.pick_up_tip()
            p20.transfer(sample_vol, s.bottom(2), d.bottom(2), new_tip='never')
            p20.mix(1, 10, d.bottom(2))
            p20.aspirate(5, d.top(2))
            p20.drop_tip()

        # transfer positive and negative controls
        for s, d in zip(tube_block.wells()[-2:], pcr_plate.wells()[-2:]):
            p20.pick_up_tip()
            p20.transfer(sample_vol, s.bottom(2), d.bottom(2), new_tip='never')
            p20.mix(1, 10, d.bottom(2))
            p20.aspirate(5, d.top(2))
            p20.drop_tip()

    else:
        sample_dest_sets = [
            row[i*3:(i+1)*3] for i in range(4) for row in pcr_plate.rows()
        ][:NUM_SAMPLES]
        mm_dests = [
            [well for col in pcr_plate.columns()[j::3]
                for well in col][:NUM_SAMPLES] + pcr_plate.columns()[9+j][-2:]
            for j in range(3)
        ]

        # transfer mastermix
        for mm, dest_set, mm_tube in zip(
                mm_dict[MM_TYPE], mm_dests, tube_block.rows()[0][0:3]):
            mm_vol = mm['volume']
            p20.pick_up_tip()
            for d in dest_set:
                p20.transfer(mm_vol, mm_tube, d.bottom(2), new_tip='never')
                p20.blow_out(d.bottom(5))
            p20.drop_tip()

        # transfer samples to corresponding locations
        for s, d_set in zip(sources, sample_dest_sets):
            for d in d_set:
                p20.pick_up_tip()
                p20.transfer(5, s, d, new_tip='never')
                p20.mix(1, 10, d)
                p20.aspirate(5, d.top(2))
                p20.drop_tip()

        for s, d_set in zip(tube_block.wells()[-2:],
                            [row[-3:] for row in pcr_plate.rows()[-2:]]):
            for d in d_set:
                p20.pick_up_tip()
                p20.transfer(5, s, d, new_tip='never')
                p20.mix(1, 10, d)
                p20.aspirate(5, d.top(2))
                p20.drop_tip()
