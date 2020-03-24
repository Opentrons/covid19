# OT-2 COVID-19 protocols

This is the development repository for running a COVID-19 diagnostic protocol on Opentrons OT-2s.

# Questions?

If you have a question about what you see in this repository, please [post it as a GitHub issue](https://github.com/Opentrons/covid19/issues/new).

If you have a more general question about using OT-2s for COVID-19 protocols, please email covid-19@opentrons.com.

# Instructions for humans

Instructions for the manual part of this protocol (how to prepare reagents, how to set up labware, and so on) are coming soon.

# Directory structure

* `/experiments` contains the exact Python scripts that were used for certain validation experiments, so we don't get confused about which experimental results correspond to which versions of our Python code.
* `/labware` contains the custom labware definitions necessary to run these protocols.  After cloning this repository, you should configure the Opentrons App to look in this directory. (Go to **More** > **Custom Labware** > **Labware Management** > **Custom Labware Definitions Folder**.)
* `/notebooks` is for stashing random Jupyter Notebooks that we're using for developing and debugging.
* `/protocols` is for the uploadable protocols themselves.
