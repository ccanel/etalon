#!/usr/bin/env python

from os import path
import sys
# Directory containing this program.
PROGDIR = path.dirname(path.realpath(__file__))
# For click_common and common.
sys.path.insert(0, path.join(PROGDIR, ".."))
# For python_config.
sys.path.insert(0, path.join(PROGDIR, "..", "..", "etc"))

import click_common
import common
import python_config

# If True, then do not run experiments and instead only print configurations.
DRY_RUN = False
# If True, then collect tcpdump traces for every experiment.
TCPDUMP = False
# If True, then racks will be launched in serial.
SYNC = False
# The number of racks to mimic when creating the strobe schedule.
NUM_RACKS_FAKE = 8
# VOQ capacities.
SMALL_QUEUE_CAP = 16
BIG_QUEUE_CAP = 50


def maybe(fnc, do=not DRY_RUN):
    """ Executes "fnc" if "do" is True, otherwise does nothing. """
    if do:
        fnc()


def main():
    # Assemble configurations. Generate the list of configurations first so that
    # we know the total number of experiments.
    cnfs = []
    for exp in xrange(5, 5 + 1):
        night_len_us = 2**exp
        day_len_us = 9 * night_len_us
        night_len_us_tdf = int(round(night_len_us * python_config.TDF))
        day_len_us_tdf = int(round(day_len_us * python_config.TDF))
        cnfs += [{"type": "fake_strobe",
                  "num_racks_fake": NUM_RACKS_FAKE,
                  "small_queue_cap": SMALL_QUEUE_CAP,
                  "big_queue_cap": BIG_QUEUE_CAP,
                  "night_len_us": night_len_us_tdf,
                  "day_len_us": day_len_us_tdf,
                  "queue_resize": False,
                  "cc": "cubic"}]

    # Set paramters that apply to all configurations.
    for cnf in cnfs:
        # Enable the hybrid switch's packet log. This should already be enabled
        # by default.
        cnf["packet_log"] = True
        # If the night and day lengths have not been set already, then do so
        # here. Explicitly set the night and day lengths instead of relying on
        # their defaults so that we can automatically calculate the experiment
        # duration, below.
        if "night_len_us" not in cnf:
            cnf["night_len_us"] = int(round(20 * python_config.TDF))
            cnf["day_len_us"] = int(round(180 * python_config.TDF))
        if "small_queue_cap" not in cnf:
            cnf["small_queue_cap"] = SMALL_QUEUE_CAP
            cnf["big_queue_cap"] = BIG_QUEUE_CAP

    # Assemble settings. Generate the list of settings first so that we can
    # the estimated total duration.
    cnfs = [
        (cnf, {
            # Generate a flow from each machine on rack 1 to its corresponding
            # partner machine on rack 2.
            "flows": [
                {"src": "h11", "dst": "h31", "data_GB": 4, "parallel": 5}],
            "tcpdump": TCPDUMP
        }) for cnf in cnfs]

    # Total number of experiments.
    tot = len(cnfs)
    # Run experiments. Use the first experiment's CC mode to avoid unnecessarily
    # restarting the cluster.
    maybe(lambda: common.initializeExperiment(
        "iperf3", cc=cnfs[0][0]["cc"], sync=SYNC))
    for cnt, (cnf, stg)  in enumerate(cnfs, start=1):
        maybe(lambda: click_common.setConfig(cnf))
        print("--- experiment {} of {}, config:\n{}".format(cnt, tot, cnf))
        maybe(lambda: common.iperf3(stg))
    maybe(common.finishExperiment)


if __name__ == "__main__":
    main()
