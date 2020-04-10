# Protocols to run OT diagnostic stations

## Station A
This protocol replates up to 96 samples from source tubes into a 96-deepwell plate. The samples should be loaded with inactivation buffer when input into this step. Please see the note at the top of the `station_a.ot2.apiv2` script for reagent setup.

## Station B
This protocol performs RNA extraction from replated samples. The output 96-deepwell plate from station A should be placed on the magnetic module in slot 4 in this protocol.  

Reservoir 1 layout (slot 2):  
![res1](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/covid+spain/S5/reservoir_setup_UPDATE.png)  

## Station C
This protocol plates elution output from station B to a new PCR plate, along with up to 3 probes (loaded in separate mastermix tubes). To create and transfer Seegene mastermix (1 below), the user should input `Seegene` for `MM_TYPE` at the top of the script. To create and transfer the other 3 single-probe mastermixes (2-4 below), the user should input `singleplex` for `MM_TYPE`.

The components for the following reagent map correspond to the 4 possible mastermix formulas (volume per sample):
  1. Seegene (17µl mix, 8µl sample)
    * component 1: 5µl nCov MOM
    * component 2: 5µl RNase-free H2O
    * component 3: 5µl 5x real time one-step buffer
    * component 4: 2µl real time one-step enzyme
  2. E gene (20µl mix, 5µl sample)
    * component 5: 5µl Rxn buffer 5x
    * component 6: 1µl dNTPs mix
    * component 7: 2µl Primer F
    * component 8: 2µl Primer R
    * component 9: 1µl Enzyme Mix
    * component 10: 8µl H20
    * component 11: 1µl E gene sonda/probe
  3. S gene (20µl mix, 5µl sample)
    * component 5: 5µl Rxn buffer 5x
    * component 6: 1µl dNTPs mix
    * component 7: 2µl Primer F
    * component 8: 2µl Primer R
    * component 9: 1µl Enzyme Mix
    * component 10: 9µl H20
  4. human RNA genes (20µl mix, 5µl sample)
    * component 5: 5µl Rxn buffer 5x
    * component 6: 1µl dNTPs mix
    * component 7: 2µl Primer F
    * component 8: 2µl Primer R
    * component 9: 1µl Enzyme Mix
    * component 10: 8µl H20
    * component 12: 1µl RNasP gene sonda/probe

Reagent 2ml screw tubes aluminum block map (slot 5):  
![reagent map](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/covid+spain/S5/mastermix_map_UPDATE2.png)
