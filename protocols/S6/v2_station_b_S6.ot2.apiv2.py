import math
from opentrons.types import Point
from opentrons import protocol_api
from opentrons.protocol_api.labware import OutOfTipsError

# metadata
metadata = {
    'protocolName': 'S2 Station B Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - binding bead mix: channels 1-6
    - elution buffer: channel 12

"""

NUM_SAMPLES = 8

DEEPWELL_Z_OFFSET = 0.5
DEEPWELL_X_OFFSET = 1


def run(ctx: protocol_api.ProtocolContext):

# load labware and modules
    tempdeck = ctx.load_module('tempdeck', '1')
    elution_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul',
        'cooled elution plate')
    reagent_res = ctx.load_labware(
        'nest_12_reservoir_15ml', '2', 'reagent reservoir 1')
    magdeck = ctx.load_module('magdeck', '4')
    magplate = magdeck.load_labware(
        'nest_96_deepwell_2ml')
    magdeck.disengage()
    etoh = ctx.load_labware(
        'nest_1_reservoir_195ml', '5', 'reservoir for ethanol').wells()[0]
    waste = ctx.load_labware(
        'nest_1_reservoir_195ml', '7', 'waste reservoir').wells()[0]
    wash_buffer = ctx.load_labware(
        'nest_12_reservoir_15ml', '8', 'reservoir for wash buffer').wells()

    if NUM_SAMPLES < 16:
        tuberack = ctx.load_labware(
            'mhs_24_tuberack_2ml', '10', 'tuberack for elution buffer')
        tips300 = [
            ctx.load_labware(
                'opentrons_96_filtertiprack_200ul', slot, '200µl filter tiprack')
            for slot in ['3', '6', '9', '11']]
    else:
        tips300 = [
            ctx.load_labware(
                'opentrons_96_filtertiprack_200ul', slot, '200µl filter tiprack')
            for slot in ['3', '6', '9', '10', '11']]

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = [well for well in magplate.rows()[0]][:num_cols]
    elution_samples_m = [well for well in elution_plate.rows()[0]][:num_cols]

    beads = reagent_res.wells()[0:6]
    if NUM_SAMPLES < 16:
        elution_buffer = tuberack.wells()[0]
    else:
        elution_buffer = reagent_res.wells()[-1]

    # pipette
    if NUM_SAMPLES < 16:
        p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300)

    # P300 multi-channel pipette properties
    working_volume = min(m300.max_volume, m300.tip_racks[0]['A1'].max_volume)
    aspirate_flow_rate = m300.flow_rate.aspirate
    dispense_flow_rate = m300.flow_rate.dispense

    def pick_up(pip):
        """
        Pick up tip if available; otherwise, pause protocol and prompt user to
        replace tipracks and reset all tipracks associated with that pipette when
        protocol is resumed
        """
        try:
            pip.pick_up_tip()
        except OutOfTipsError:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before '
                      'resuming.')
            pip.reset_tipracks()
            pick_up(pip)

    def remove_supernatant(vol, blow_out=False):
        """
        Remove supernatant from deep well plate, avoiding the magbead pellet
        """
        m300.flow_rate.aspirate = aspirate_flow_rate * 2/3
        m300.flow_rate.dispense = dispense_flow_rate * 2/3

        transfer_vol = working_volume - m300.min_volume
        num_trans = math.ceil(vol/transfer_vol)

        for i, m in enumerate(mag_samples_m):
            side = -1 if i < 6 else 1
            loc = get_deep_well_loc(m, side)
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for _ in range(num_trans):
                if m300.current_volume > 0:
                    m300.dispense(location=m.top(-10))
                m300.move_to(m.center())
                m300.aspirate(transfer_vol, loc)
                m300.air_gap()
                if blow_out == False:
                    m300.default_speed = 100
                m300.dispense(location=waste.top(-3))
                if blow_out == True:
                    m300.blow_out()
                m300.aspirate(30)
            m300.return_tip()
            m300.default_speed = 400

    def get_deep_well_loc(well, side):
        """Return location in the deep well plate based on the loc of the magbead pellet
        """
        loc = well.bottom(DEEPWELL_Z_OFFSET).move(Point(x=side*DEEPWELL_X_OFFSET))
        return loc

    # premix, transfer, and mix magnetic beads with sample
    for i, m in enumerate(mag_samples_m):
        pick_up(m300)

        # resuspend beads by mixing each column 20 times at 200 µL slowly
        if i % 2 == 0:
            m300.flow_rate.aspirate = aspirate_flow_rate * 1/2
            m300.flow_rate.dispense = dispense_flow_rate * 2/3
            for j in range(20):
                m300.aspirate(160, beads[i//2].bottom(0.5))
                m300.dispense(160, beads[i//2].bottom(3))

        # transfer 550 µL beads to each sample
        for vol in [180, 180, 190]:
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            m300.aspirate(vol, beads[i//2])
            m300.default_speed = 50
            m300.flow_rate.dispense = dispense_flow_rate * 3/16
            m300.dispense(vol, m.bottom(6))
            m300.drop_tip()
            m300.default_speed = 400

    ctx.pause('(1) Seal the plate, and shake for 2 minuts at 1,050 rpm. '
    '(2) Incubate the sealed plate at 65°C for 5 minutes. (3) Shake the plate '
    'for 5 minutes at 1,050 rpm. (4) Remove seal and place the plate back on '
    'the magdeck.')

    # incubate on magnet
    magdeck.engage()
    ctx.delay(minutes=10, msg='Incubating on magnet for 10 minutes.')

    # remove supernatant
    remove_supernatant(810)

    m300.flow_rate.aspirate = aspirate_flow_rate
    m300.flow_rate.dispense = dispense_flow_rate
    transfer_vol = working_volume - m300.min_volume  # transfer volume for bead wash

    # wash with wash buffer
    magdeck.disengage()
    for m, wash_buff in zip(mag_samples_m, wash_buffer):
        pick_up(m300)
        num_trans = math.ceil(1000/transfer_vol)

        for _ in range(num_trans):
            if m300.current_volume > 0:
                m300.dispense(location=wash_buff.top(-3))  # remove air gap if any
            m300.aspirate(transfer_vol, wash_buff.bottom(0.25))
            m300.air_gap()
            m300.default_speed = 100
            m300.dispense(transfer_vol, m.top(-10))
            m300.air_gap(20, height=-10)

        m300.dispense(20, m.top(-10)) # dispense air gap
        m300.mix(10, 180, m.bottom(0.5))
        m300.air_gap(20, height=-10)
        m300.drop_tip()

        m300.default_speed = 400

    # incubate on magnet
    magdeck.engage()
    ctx.delay(minutes=2, msg='Incubating on magnet for 2 minutes.')

    # remove supernatant
    remove_supernatant(1010, blow_out=False)

    m300.flow_rate.aspirate = aspirate_flow_rate
    m300.flow_rate.dispense = dispense_flow_rate

    # wash with EtOH
    for vol in [1000, 500]:
        magdeck.disengage()

        for m in mag_samples_m:
            pick_up(m300)
            num_trans = math.ceil(vol/transfer_vol)

            for _ in range(num_trans):
                if m300.current_volume > 0:
                    m300.dispense(location=etoh.top(-3))  # remove air gap if any
                m300.aspirate(transfer_vol, etoh.bottom(0.25))
                m300.air_gap()
                m300.dispense(transfer_vol, m.top(-10))
                m300.blow_out(m.top(-10))
                m300.air_gap(20, height=-10)  # air gap to prevent dripping

            m300.dispense(20, m.top(-10))
            m300.mix(10, 180, m.bottom(0.5))
            m300.blow_out(m.top(-10))
            m300.air_gap(20, height=-10)
            m300.drop_tip()

        # incubate on magnet
        magdeck.engage()
        ctx.delay(minutes=2, msg='Incubating on magnet for 2 minutes.')

        # remove supernatant
        remove_supernatant(vol+10, blow_out=True)

    ctx.delay(minutes=2, msg="Airdrying beads for 2 minutes.")

    m300.default_speed = 400
    m300.aspirate_flow_rate = aspirate_flow_rate * 4/5
    m300.dispense_flow_rate = dispense_flow_rate * 4/5
    magdeck.disengage()

    # transfer elution buffer to samples
    if NUM_SAMPLES < 16:
        pip = p300
        sample_dests = [
            well for col in magplate.columns()[0::2]
            for well in col][:NUM_SAMPLES]
    else:
        pip = m300
        sample_dests = mag_samples_m
    for i, m in enumerate(sample_dests):
        pick_up(pip)
        pip.aspirate(50, elution_buffer.bottom(0.25))
        pip.dispense(50, m)
        pip.blow_out(m.bottom(5))
        pip.aspirate(20)
        pip.drop_tip()

    ctx.pause('(1) Seal the plate and shake for 5 minutes at 1,050 rpm. (2) '
    'Incubate the sealed plate at 65°C for 10 minutes. (3) Shake the plate '
    'for 5 minutes at 1,050 rpm. (4) Remove the seal and place the plate back '
    'on the magdeck.')

    # incubate on magnet
    magdeck.engage()
    ctx.delay(minutes=3, msg='Incubating on magnet for 3 minutes.')

    # transfer elution to clean plate
    m300.flow_rate.aspirate = aspirate_flow_rate * 5/6
    for i, (s, d) in enumerate(zip(mag_samples_m, elution_samples_m)):
        pick_up(m300)
        side = -1 if i < 6 else 1
        loc = get_deep_well_loc(s, side)
        m300.aspirate(50, loc)
        m300.dispense(50, d)
        m300.blow_out(d.top(-3))
        m300.aspirate(20, d.top())
        m300.drop_tip()
