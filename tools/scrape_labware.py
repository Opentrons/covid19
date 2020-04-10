import argparse
import opentrons.simulate
import opentrons.protocol_api.labware
import json
import urllib

def is_labware(maybe_labware):
    return isinstance(maybe_labware, opentrons.protocol_api.labware.Labware)

parser = argparse.ArgumentParser(description="Simulate an Opentrons Python Protocol API script and print a protocol-library-kludge URL to get its deck map.")
parser.add_argument("file", type=argparse.FileType())
args = parser.parse_args()

# Compile the code to exec to preserve its filename, for clearer error messages.
code = compile(args.file.read(), args.file.name, "exec", dont_inherit=True)
exec_globals = {}
exec(code, exec_globals)

context = opentrons.simulate.get_protocol_api(exec_globals["metadata"]["apiLevel"])
exec_globals["run"](context)

labware_slots = {slot: maybe_labware for slot, maybe_labware in context.deck.items() if is_labware(maybe_labware)}
labware_spec = {int(slot): {"labwareType": labware.load_name, "name": ""} for slot, labware in labware_slots.items()}

# This expects you to be running a local protocol-library-kludge server.
# See: https://github.com/Opentrons/opentrons/tree/0adc97e070ec377047ef1c36ad5bc2739f19111d/protocol-library-kludge
print("localhost:8080?data="+urllib.parse.quote(json.dumps({"labware": labware_spec})))

# To do:
# - Support custom labware in this script with a -L option.  See opentrons_simulate.
# - Copy the protocol-library-kludge source into this repo.
# - Teach it to display our custom labware.
# - Change it to show the labware names all the time, not just on hover?
# - Have it output just the SVG, not an HTML page.
# - Automatically run the server and save the file from this script.