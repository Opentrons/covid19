# Introduction

[Opentrons](https://opentrons.com/) is working with the [Open Medicine Institute](https://www.openmedicineinstitute.org/) to automate COVID-19 diagnostics on a fleet of [OT-2 robots](https://opentrons.com/ot-2).

This is our development repository.  Welcome!  Here, you'll find:

* The scripts that run on the robots, written with the [OT-2 Python Protocol API](https://docs.opentrons.com/v2/).
* [Labware definition](https://support.opentrons.com/en/articles/3136501-what-is-a-labware-definition) files.
* Some of our experimental notes and reports.

We're actively developing and testing these protocols, so things might be a little messy.  We're publishing our works in progress here so that other labs might benefit from them as quickly as possible.

# How it works

We're automating a RT-qPCR based diagnostic protocol.  We split it into 3 parts, intended to be run on 3 separate robots:

* **Station A:** Sample intake
* **Station B:** RNA extraction
* **Station C:** qPCR setup

See [the Python files](protocols) for more details.

# Reagent preparation and handling

Instructions for the manual part of this protocol (how to prepare reagents, how to set up labware, and so on) are hosted [on protocols.io](https://www.protocols.io/groups/opentrons-covid19-testing/publications).

# Directory structure

* `/experiments` contains the exact Python scripts that were used for certain validation experiments, so we don't get confused about which experimental results correspond to which versions of our Python code.
* `/labware` contains the custom labware definitions necessary to run these protocols.  After cloning this repository, you should configure the Opentrons App to look in this directory. (Go to **More** > **Custom Labware** > **Labware Management** > **Custom Labware Definitions Folder**.)
* `/notebooks` is for stashing random Jupyter Notebooks that we're using for developing and debugging.
* `/protocols` is for the uploadable protocols themselves.

# Where to ask questions

If you have a question about what you see in this repository, please [post it as a GitHub issue](https://github.com/Opentrons/covid19/issues/new).

If you have a more general question about using OT-2s for COVID-19 protocols, please email covid-19@opentrons.com.
