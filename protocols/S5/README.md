# Protocols to run OT diagnostic stations

## Station A
This protocol replates up to 96 samples from source tubes into a 96-deepwell plate. The samples should be loaded with inactivation buffer when input into this step. Please see the note at the top of the `station_a.ot2.apiv2` script for reagent setup.

## Station B
This protocol performs RNA extraction from replated samples. The output 96-deepwell plate from station A should be placed on the magnetic module in slot 4 in this protocol. Please see the note at the top of the `station_b.ot2.apiv2` script for reagent setup.

## Station C
This protocol plates elutions output from station B to a new PCR plate, along with up to 3 probes (loaded in separate mastermix tubes). Please see the note at the top of the `station_c.ot2.apiv2` script for reagent setup.
