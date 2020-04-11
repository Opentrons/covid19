# Protocols to run OT diagnostic stations

## Station A
This protocol replates up to 96 samples from source tubes into a 96-deepwell plate. The samples should be loaded with inactivation buffer when input into this step. Please see the note at the top of the `station_a.ot2.apiv2` script for reagent setup.

## Station B
This protocol performs RNA extraction from replated samples. The output 96-deepwell plate from station A should be placed on the magnetic module in slot 4 in this protocol.  

Reservoir 1 layout (slot 2):  
![res1](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/covid+spain/S5/reservoir_setup_UPDATE.png)  

## Station C
This protocol plates elution output from station B to a new PCR plate, along with up to 3 probes (loaded in separate mastermix tubes).  

The components for the following reagent map correspond to 1 of 4 possible mastermix formulas:
  1. Seegene (17µl mix, 8µl sample)
    * component 1: nCov MOM
    * component 2: RNase-free H2O
    * component 3: 5x real time one-step buffer
    * component 4: real time one-step enzyme
  2. E gene (20µl, 5µl sample)
    * component 1: H20
    * component 2: Rxn buffer 5x
    * component 3: dNTPs mix
    * component 4: Primer F
    * component 5: Primer R
    * component 6: Enzyme Mix
    * component 7: sonda/probe
  3. S gene (20µl, 5µl sample)
    * component 1: H20
    * component 2: Rxn buffer 5x
    * component 3: dNTPs mix
    * component 4: Primer F
    * component 5: Primer R
    * component 6: Enzyme Mix
  4. human RNA genes (20µl, 5µl sample)
    * component 1: H20
    * component 2: Rxn buffer 5x
    * component 3: dNTPs mix
    * component 4: Primer F
    * component 5: Primer R
    * component 6: Enzyme Mix
    * component 7: sonda/probe

Reagent 2ml screw tubes aluminum block map (slot 5):  
![reagent map](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/covid+spain/S5/valldhebron_mastermix_map.png)
