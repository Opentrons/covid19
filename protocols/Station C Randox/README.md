# Station C: Randox Pathway

This folder contains 3 protocols for running Station C: one 24-sample version and two 48-sample versions.

In all three versions, the following labware layout remains constant:
- Slot 3: 20ul Filter Tips
- Slot 4: Temp Module + 96-well Al block + PCR Plate
- Slot 5: Opentrons 24 Tube Rack + 1.5mL tube with master mix in A1

`StationC-Randox-24.py`
This protocol takes 24 samples from a single elution plate (in slot 1, columns 1/2/3) and transfers the samples to the PCR plate on the temperature module (columns 1/2/3) containing master mix

`StationC-Randox-48-one-input.py`
This protocol takes 48 samples from a single elution plate (in slot 1, columns 1/2/3/4/5/6) and transfers the samples to the PCR plate on the temperature module (columns 1/2/3/4/5/6) containing master mix

`StationC-Randox-48-two-input.py`
This protocol takes 24 samples from TWO elution plates (in slots 1 and 2, columns 1/2/3) and transfers the samples to the PCR plate on the temperature module (columns 1/2/3/4/5/6) containing master mix
