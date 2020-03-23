# Protocols to run OT diagnostic stations

## Station B
The current protocol (for extracting from 8 samples) is V15-StationB-8samples.py

## Station C
The current protocol is station-C-qpcr-map.py.

The qPCR build map is defined in the two MAP constants at the top, with a tab-separated list of which wells get which master mixes and samples. Copy the protocol to a subdirectory of ../experiments/
if you're modifying this protocol to run a specific experiment. The tab-separated maps can be filled by directly copying a 12x8 grid of cells from a google sheet; see
https://docs.google.com/spreadsheets/d/1agwFQ2PMsGSy4fmdY-3Hq_IEjcIYMUT-2Q5yhyfY7Fk/edit#gid=1878235427 for an example.
