# Protocols to run OT diagnostic stations

## Station B
The current protocol (for extracting from 8 samples) is V15-StationB-8samples.py

## Station C
The current protocol is station-C-qpcr-map.py.

The qPCR build map is defined in the two `MAP` constants at the top, `MASTER_MIX_MAP` and `SAMPLE_MAP`, with a tab-separated list of which wells get which master mixes and samples. The tab-separated maps can be filled by directly copying a 12x8 grid of cells from a google sheet; see
https://docs.google.com/spreadsheets/d/1EF5goRfT6f6d0IyCboaYNDJns9UazWaFNT4N8_CPyzQ/edit?usp=sharing for an example.

To run a new experiment, create a dated and named experiment in the `/experiments` directory of this repository, and copy the protocol into it. Modify the MAP variables to reflect the experiment being performed. This creates a long term record of the protocol and plate layout used during that experiment.

Depending on the qPCR machine you plan to use, you may also need to modify the labware used for the qPCR build plate. Modify the `QPCR_LABWARE` constant if this is the case. If you need to add a custom labware definition, place it in the `/labware` directory of this repository.
