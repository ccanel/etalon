#!/usr/bin/env python

from os import path
import sys
# Directory containing this program.
PROGDIR = path.dirname(path.realpath(__file__))
# For click_common and common.
sys.path.insert(0, path.join(PROGDIR, ".."))
# For python_config.
sys.path.insert(0, path.join(PROGDIR, "..", "..", "etc"))
import time

import click_common
import common
import python_config

# If True, then do not run experiments and instead only print configurations.
DRY_RUN = False
# If True, then collect tcpdump traces for every experiment.
TCPDUMP = False
# If True, then racks will be launched in serial.
SYNC = False
# How much to grow the delay (and ToR queues by).
SCALING_FACTOR = 5.
# Amount of data to send.
DATA_B = int(round(4e9))
# TCP variant.
CC = "cubic"
# Circuit downtime between configurations.
NIGHT_LEN_US = 0
# Source rack for traffic flows.
SRC_RACK = 1
# How long in advance to resize ToR queues.
IN_ADVANCE_US = 0

# # Long sweep settings.
# BASE_DELAYS_US = [100, 200, 500, 1000]
# QUEUE_CAPS = [50, 100, 200, 400]
# NW_SWITCH_POW_MIN = 12
# NW_SWITCH_POW_MAX = 40
# NW_SWITCH_US = [
#     2 ** (nw_switch_pow / 2.)
#     for nw_switch_pow in xrange(NW_SWITCH_POW_MIN, NW_SWITCH_POW_MAX + 1)]
# PARS = [1, 5, 10, 20]

# Short sweep settings.
BASE_DELAYS_US = [100, 500, 1000]
QUEUE_CAPS = [100, 200, 400]
NW_SWITCH_POW_MIN = 6
NW_SWITCH_POW_MAX = 20
NW_SWITCH_USs = [
    2 ** nw_switch_pow
    for nw_switch_pow in xrange(NW_SWITCH_POW_MIN, NW_SWITCH_POW_MAX + 1)]
PARS = [5, 10, 20]


def maybe(fnc, do=not DRY_RUN):
    """ Executes "fnc" if "do" is True, otherwise does nothing. """
    if do:
        fnc()


def main():
    # Assemble settings. Generate the list of settings first so that we know the
    # total number of experiments.
    stgs = [
        (
            {
                "type": "fixed",
                # Define a cycle schedule, where each rack connects to the next
                # rack. A week consists of one day and one night. The day length
                # is set to the desired network reconfiguration period. The
                # night length is (probably) set to 0.
                "fixed_schedule": (
                    "2 {day_len_us} {day_config} {night_len_us} {night_config}"
                ).format(
                    day_len_us=int(round(nw_switch_us * python_config.TDF)),
                    day_config="".join([
                        "{}/".format((rack + 1) % python_config.NUM_RACKS)
                        for rack in xrange(python_config.NUM_RACKS)])[:-1],
                    night_len_us=int(round(NIGHT_LEN_US * python_config.TDF)),
                    night_config=('-1/' * python_config.NUM_RACKS)[:-1]),
                "small_queue_cap": queue_cap,
                "big_queue_cap": int(round(queue_cap * SCALING_FACTOR)),
                "small_nw_delay_us": delay_us,
                "big_nw_delay_us": int(round(delay_us * SCALING_FACTOR)),
                "queue_resize": True,
                "in_advance": int(round(IN_ADVANCE_US * python_config.TDF)),
                "packet_log": True,
                "cc": CC,
                "details": "{}-{}-{}-{}".format(
                    delay_us, nw_switch_us, queue_cap, par)
            },
            {
                # Generate a number of parallel flows from the first host on rack 1
                # to the first host on rack 2.
                "flows": [
                    {
                        "src": "h{}{}".format(SRC_RACK, 1),
                        # The schedule is a cycle, so the destination rack is
                        # the the rack after the source rack.
                        "dst": "h{}{}".format(
                            (SRC_RACK + 1) % python_config.NUM_RACKS, 1),
                        "data_B": DATA_B,
                        "parallel": par
                    }
                ],
                "tcpdump": TCPDUMP
            }
        )
        for delay_us in BASE_DELAYS_US
        for nw_switch_us in NW_SWITCH_USs
        for queue_cap in QUEUE_CAPS
        for par in PARS]
    stgs = stgs[:2]
    # Total number of experiments.
    tot = len(stgs)
    tot_srt_s = time.time()
    # Run experiments. Use the first experiment's CC mode to avoid unnecessarily
    # restarting the cluster.
    maybe(lambda: common.initializeExperiment(
        "iperf3", cc=stgs[0][0]["cc"], sync=SYNC))
    for cnt, stg  in enumerate(stgs, start=1):
        cnf, flw_stgs = stg
        maybe(lambda cnf_=cnf: click_common.setConfig(cnf_))
        print("--- experiment {} of {}, config:\n{}".format(cnt, tot, stg))
        exp_srt_s = time.time()
        maybe(lambda flw_stgs_=flw_stgs: common.iperf3(flw_stgs_))
        print("Experiment duration: {:.2f} seconds".format(
            time.time() - exp_srt_s))
    maybe(common.finishExperiment)
    print("Total experiment duration: {:.2f} seconds".format(
        time.time() - tot_srt_s))


if __name__ == "__main__":
    main()
