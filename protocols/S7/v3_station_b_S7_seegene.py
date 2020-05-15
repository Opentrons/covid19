from opentrons.types import Point
import json
import os
import math
import threading
from time import sleep

metadata = {
    'protocolName': 'Version 3 S7 Station B Seegene (200µl sample input)',
    'author': 'Nick <ndiehl@opentrons.com',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 94  # start with 8 samples, slowly increase to 48, then 94 (max is 94)
ELUTION_VOLUME = 40
TIP_TRACK = False

# Definitions for deck light flashing
class CancellationToken:
    def __init__(self):
       self.is_continued = False

    def set_true(self):
       self.is_continued = True

    def set_false(self):
       self.is_continued = False


def turn_on_blinking_notification(hardware, pause):
    while pause.is_continued:
        hardware.set_lights(rails=True)
        sleep(1)
        hardware.set_lights(rails=False)
        sleep(1)

def create_thread(ctx, cancel_token):
    t1 = threading.Thread(target=turn_on_blinking_notification, args=(ctx._hw_manager.hardware, cancel_token))
    t1.start()
    return t1

# Start protocol
def run(ctx):
    # Setup for flashing lights notification to empty trash
    cancellationToken = CancellationToken()

    # load labware and pipettes
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filtertiprack')
               for slot in ['3', '6', '8', '9', '10']]
    parkingrack = ctx.load_labware(
        'opentrons_96_tiprack_300ul', '7', 'empty tiprack for parking')

    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'left', tip_racks=tips300)

    magdeck = ctx.load_module('magdeck', '4')
    magdeck.disengage()
    magheight = 13.7
    magplate = magdeck.load_labware('nest_96_deepwell_2ml')
    # magplate = magdeck.load_labware('biorad_96_wellplate_200ul_pcr')
    tempdeck = ctx.load_module('Temperature Module Gen2', '1')
    flatplate = tempdeck.load_labware(
                'opentrons_96_aluminumblock_nest_wellplate_100ul',)
    waste = ctx.load_labware('nest_1_reservoir_195ml', '11',
                             'Liquid Waste').wells()[0].top()
    res1 = ctx.load_labware(
        'nest_12_reservoir_15ml', '5', 'reagent reservoir 1')
    res2 = ctx.load_labware(
        'nest_12_reservoir_15ml', '2', 'reagent reservoir 2')
    bind_buffer = res1.wells()[:6]
    wash1 = res1.wells()[6:10]
    wash2 = res2.wells()[:4]
    wash3 = res2.wells()[4:8]
    water = res2.wells()[8]

    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = magplate.rows()[0][:num_cols]
    elution_samples_m = flatplate.rows()[0][:num_cols]
    parking_spots = parkingrack.rows()[0][:num_cols]

    magdeck.disengage()  # just in case
    tempdeck.set_temperature(4)

    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 300

    folder_path = '/data/B'
    tip_file_path = folder_path + '/tip_log.json'
    tip_log = {'count': {}}
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips300' in data:
                    tip_log['count'][m300] = data['tips300']
                else:
                    tip_log['count'][m300] = 0
        else:
            tip_log['count'][m300] = 0
    else:
        tip_log['count'] = {m300: 0}

    tip_log['tips'] = {
        m300: [tip for rack in tips300 for tip in rack.rows()[0]]}
    tip_log['max'] = {m300: len(tip_log['tips'][m300])}

    def pick_up(pip, loc=None):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip] and not loc:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        if loc:
            pip.pick_up_tip(loc)
        else:
            pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
            tip_log['count'][pip] += 1

    switch = True
    drop_count = 0
    drop_threshold = 120  # number of tips trash will accommodate before prompting user to empty

    def drop(pip):
        nonlocal switch
        nonlocal drop_count
        side = 30 if switch else -18
        drop_loc = ctx.loaded_labwares[12].wells()[0].top().move(
            Point(x=side))
        pip.drop_tip(drop_loc)
        switch = not switch
        drop_count += 8
        if drop_count == drop_threshold:
            # Setup for flashing lights notification to empty trash
            if not ctx._hw_manager.hardware.is_simulator:
                cancellationToken.set_true()
            thread = create_thread(ctx, cancellationToken)
            ctx.pause('Please empty tips from waste before resuming.')

            ctx.home()  # home before continuing with protocol
            cancellationToken.set_false() # stop light flashing after home
            thread.join()
            drop_count = 0

    waste_vol = 0
    waste_threshold = 185000

    def waste_track(vol):
        nonlocal waste_vol
        # print(waste_vol)
        if waste_vol + vol >= waste_threshold:
            # Setup for flashing lights notification to empty liquid waste
            if not ctx._hw_manager.hardware.is_simulator:
                cancellationToken.set_true()
            thread = create_thread(ctx, cancellationToken)
            ctx.pause('Please empty liquid waste (slot 11) before resuming.')

            ctx.home()  # home before continuing with protocol
            cancellationToken.set_false() # stop light flashing after home
            thread.join()
            waste_vol = 0
        waste_vol += vol

    def remove_supernatant(vol, parking_pickup=False, parking_drop=False):
        m300.flow_rate.aspirate = 30
        num_trans = math.ceil(vol/200)
        vol_per_trans = vol/num_trans
        for i, (m, spot) in enumerate(zip(mag_samples_m, parking_spots)):
            if parking_pickup:
                pick_up(m300, spot)
            else:
                pick_up(m300)
            side = -1 if i % 2 == 0 else 1
            loc = m.bottom(0.5).move(Point(x=side*2))
            for _ in range(num_trans):
                waste_track(vol_per_trans*8)  # track liquid in waste reservoir
                if m300.current_volume > 0:
                    m300.dispense(m300.current_volume, m.top())  # void air gap if necessary
                m300.move_to(m.center())
                m300.transfer(vol_per_trans, loc, waste, new_tip='never',
                              air_gap=20)
                m300.blow_out(waste)
                m300.air_gap(20)
            if parking_drop:
                m300.drop_tip(spot)
            else:
                drop(m300)
        m300.flow_rate.aspirate = 150

    def wash(wash_vol, source, mix_time_minutes=0, resuspend=True):
        num_trans = math.ceil(wash_vol/200)
        vol_per_trans = wash_vol/num_trans

        if resuspend:
            magdeck.disengage()
            for i, (m, spot) in enumerate(zip(mag_samples_m, parking_spots)):
                pick_up(m300)
                side = 1 if i % 2 == 0 else -1
                loc = m.bottom(0.5).move(Point(x=side*2))
                src = source[i//4]
                for n in range(num_trans):
                    if m300.current_volume > 0:
                        m300.dispense(m300.current_volume, src.top())
                    m300.transfer(vol_per_trans, src, m.top(), air_gap=20,
                                  new_tip='never')
                    if n < num_trans - 1:  # only air_gap if going back to source
                        m300.air_gap(20)
                m300.mix(10, 150, loc)  # resuspend
                m300.blow_out(m.top())
                m300.air_gap(20)
                m300.drop_tip(spot)

            ctx.comment('Incubating at room temp for \
~' + str(mix_time_minutes) + ' minutes with mixing.')
            mix_sets = math.ceil(mix_time_minutes*2/num_cols)  # calculate number of mix sets
            park = True if num_cols > 1 else False  # don't go back and forth to parking rack if 1 column
            if not park:
                pick_up(m300, parking_spots[0])
            for mix in range(mix_sets):
                for well, spot in zip(mag_samples_m, parking_spots):
                    if park:
                        pick_up(m300, spot)
                    m300.mix(10, 200, well)
                    m300.blow_out(well.top(-2))
                    m300.air_gap(20)
                    if park:
                        m300.drop_tip(spot)
            if not park:
                m300.drop_tip(parking_spots[0])

            magdeck.engage(height=magheight)
            ctx.delay(seconds=30, msg='Incubating on MagDeck for 30 seconds.')

        else:
            magdeck.engage(magheight)
            for i, (m, spot) in enumerate(zip(mag_samples_m, parking_spots)):
                pick_up(m300)
                src = source[i//4]
                for n in range(num_trans):
                    if m300.current_volume > 0:
                        m300.dispense(m300.current_volume, src.top())
                    m300.transfer(vol_per_trans, src, m.top(), air_gap=20,
                                  new_tip='never')
                    if n < num_trans - 1:  # only air_gap if going back to source
                        m300.air_gap(20)
                m300.blow_out(m.top())
                m300.air_gap(20)
                m300.drop_tip(spot)

        remove_supernatant(math.ceil(wash_vol/200)*200, parking_pickup=True,
                           parking_drop=False)

    # add bead binding buffer and mix samples
    for i, (well, spot) in enumerate(zip(mag_samples_m, parking_spots)):
        source = bind_buffer[i//2]
        pick_up(m300)
        for _ in range(5):
            m300.aspirate(180, source.bottom(0.5))
            m300.dispense(180, source.bottom(5))
        for t in range(3):
            if m300.current_volume > 0:
                m300.dispense(m300.current_volume, source.top())  # void air gap if necessary
            m300.transfer(200, source, well.top(), air_gap=20,  # total 600µl binding buffer
                          new_tip='never')
            if t < 2:
                m300.air_gap(20)
        m300.mix(5, 200, well)
        m300.blow_out(well.top(-2))
        m300.air_gap(20)
        m300.drop_tip(spot)

    # ctx.comment('Incubating at room temp for ~5 minutes with mixing.')
    # park = True if num_cols > 1 else False  # don't go back and forth to parking rack if 1 column
    # if not park:
    #     pick_up(m300, parking_spots[0])
    # for mix in range(2):
    #     for well, spot in zip(mag_samples_m, parking_spots):
    #         if park:
    #             pick_up(m300, spot)
    #         m300.mix(10, 200, well)
    #         m300.blow_out(well.top(-2))
    #         m300.air_gap(20)
    #         if park:
    #             m300.drop_tip(spot)
    # if not park:
    #     m300.drop_tip(parking_spots[0])

    magdeck.engage(height=magheight)
    ctx.delay(minutes=2, msg='Incubating on MagDeck for 2 minutes.')

    # remove initial supernatant
    remove_supernatant(1200, parking_pickup=True, parking_drop=False)

    # washes
    wash(490, wash1, 1.5)
    wash(490, wash2, 0.5)
    ctx.delay(minutes=25, msg='Airdrying beads at room temperature for 25 \
minutes.')
    wash(500, wash3, resuspend=False)

    magdeck.disengage()

    # resuspend beads in elution
    for i, (m, spot) in enumerate(zip(mag_samples_m, parking_spots)):
        pick_up(m300)
        side = 1 if i % 2 == 0 else -1
        loc = m.bottom(0.5).move(Point(x=side*2))
        m300.aspirate(ELUTION_VOLUME*1.25, water)
        m300.move_to(m.center())
        m300.dispense(ELUTION_VOLUME*1.25, loc)
        m300.mix(10, ELUTION_VOLUME, loc)
        m300.blow_out(m.bottom(5))
        m300.air_gap(20)
        m300.drop_tip(spot)

#     ctx.delay(minutes=2, msg='Incubating off magnet at room temperature for 2 \
# minutes')
    magdeck.engage(height=magheight)
    ctx.delay(minutes=5, msg='Incubating on magnet at room temperature for 5 \
minutes')

    for i, (m, e, spot) in enumerate(
            zip(mag_samples_m, elution_samples_m, parking_spots)):
        pick_up(m300, spot)
        side = -1 if i % 2 == 0 else 1
        loc = m.bottom(0.5).move(Point(x=side*2))
        m300.transfer(ELUTION_VOLUME, loc, e.bottom(5), air_gap=20,
                      new_tip='never')
        m300.blow_out(e.top(-2))
        m300.air_gap(20)
        m300.drop_tip()

    # Setup for flashing lights notification for protocol completion
    if not ctx._hw_manager.hardware.is_simulator:
        cancellationToken.set_true()
    thread = create_thread(ctx, cancellationToken)
    ctx.pause('Protocol complete! Please transfer the plate in slot 1.')

    ctx.home()  # home before continuing with protocol
    cancellationToken.set_false() # stop light flashing after home
    thread.join()
