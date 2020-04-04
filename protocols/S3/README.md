# Protocols to run OT diagnostic stations

## Station A
This protocol replates up to 96 samples from source tubes into a 96-deepwell plate. The samples should be loaded with inactivation buffer when input into this step. Please see the note at the top of the `station_a.ot2.apiv2` script for reagent setup.

## Station B
This protocol performs RNA extraction from replated samples. The output 96-deepwell plate from station A should be placed on the magnetic module in slot 4 in this protocol.  

Reservoir 1 layout (slot 2):  
![res1](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/covid+spain/res1_layout.png)  

Reservoir 2 layout (slot 5):  
![res2](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/covid+spain/res2_layout.png)

## Station C
This protocol plates elution output from station B to a new PCR plate, along with up to 3 probes (loaded in separate mastermix tubes).  

2ml Eppendorf tuberack layout (slot 5):
![tuberack](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/covid+spain/station_c_tuberack.png)
