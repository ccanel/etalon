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
# If True, then record the hybrid switch packet log.
PACKET_LOG = False
# If True, then racks will be launched in serial.
SYNC = False
# Amount of data to send.
DATA_B = 4e9
# TCP variant.
CC = "cubic"
# Circuit downtime between configurations.
NIGHT_LEN_US = 0
# Source rack for traffic flows. 0-indexed.
SRC_RACK = 1

# Long sweep settings.
BASE_DELAYS_US = [100, 200, 500, 1000]
QUEUE_CAPS = [50, 100, 200, 400]
NW_SWITCH_POW_MIN = 12
NW_SWITCH_POW_MAX = 40
NW_SWITCH_USs = [
    2 ** (nw_switch_pow / 2.)
    for nw_switch_pow in xrange(NW_SWITCH_POW_MIN, NW_SWITCH_POW_MAX + 1)]
PARS = [1, 5, 10, 20]
SCALING_FACTOR = 5.

# # Short sweep settings.
# BASE_DELAYS_US = [100, 500, 1000]
# QUEUE_CAPS = [100, 200, 400]
# NW_SWITCH_POW_MIN = 6
# NW_SWITCH_POW_MAX = 20
# NW_SWITCH_USs = [
#     2 ** nw_switch_pow
#     for nw_switch_pow in xrange(NW_SWITCH_POW_MIN, NW_SWITCH_POW_MAX + 1)]
# PARS = [5, 10, 20]
# SCALING_FACTOR = 5.

# # Debugging sweep settings.
# BASE_DELAYS_US = [1000]
# QUEUE_CAPS = [100]
# NW_SWITCH_POW_MIN = 20
# NW_SWITCH_POW_MAX = 20
# NW_SWITCH_USs = [
#     2 ** nw_switch_pow
#     for nw_switch_pow in xrange(NW_SWITCH_POW_MIN, NW_SWITCH_POW_MAX + 1)]
# PARS = [5]
# SCALING_FACTOR = 100.


def maybe(fnc, do=not DRY_RUN):
    """ Executes "fnc" if "do" is True, otherwise does nothing. """
    if do:
        fnc()


def main():
    get_extra_us = lambda delay_us: delay_us * (SCALING_FACTOR - 1)
    tdf = lambda val: val * python_config.TDF
    intify = lambda val: int(round(val))
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
                    day_len_us=intify(tdf(nw_switch_us)),
                    day_config="".join([
                        "{}/".format((rack + 1) % python_config.NUM_RACKS)
                        for rack in xrange(python_config.NUM_RACKS)])[:-1],
                    night_len_us=intify(tdf(NIGHT_LEN_US)),
                    night_config=('-1/' * python_config.NUM_RACKS)[:-1]),
                "small_queue_cap": queue_cap,
                "big_queue_cap": intify(queue_cap * SCALING_FACTOR),
                "circuit_link_delay": tdf(delay_us / 1e6),
                # This is *extra* delay, so the scaling factor is
                # SCALING_FACTOR - 1.
                "extra_circuit_del_s": tdf(get_extra_us(delay_us) / 1e6 *
                                           (SCALING_FACTOR - 1)),
                "queue_resize": True,
                "in_advance": intify(tdf(min(
                    0.75 * nw_switch_us, get_extra_us(delay_us)))),
                "packet_log": PACKET_LOG,
                "cc": CC,
                "details": "{}-{}-{}-{}".format(
                    delay_us, intify(nw_switch_us), queue_cap, par)
            },
            {
                # Generate a number of parallel flows from the first host on rack 1
                # to the first host on rack 2.
                "flows": [
                    {
                        "src": "h{}{}".format(SRC_RACK + 1, 1),
                        # The schedule is a cycle, so the destination rack is
                        # the the rack after the source rack.
                        "dst": "h{}{}".format(
                            ((SRC_RACK - 1) % python_config.NUM_RACKS) + 1, 1),
                        "data_B": intify(DATA_B),
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
    # Total number of experiments.
    tot = len(stgs)
    tot_srt_s = time.time()
    # Run experiments. Use the first experiment's CC mode to avoid unnecessarily
    # restarting the cluster.
    maybe(lambda: common.initializeExperiment(
        "iperf3", cc=stgs[0][0]["cc"], sync=SYNC))

    # The iperf3 integration is very fragile and prone to transient errors. This
    # loop will retry an experiment until it succeeds.
    while stgs:
        stg = stgs[-1]
        cnf, flw_stgs = stg

        maybe(lambda cnf_=cnf: click_common.setConfig(cnf_))
        print("--- {} of {} experiments remaining, config:\n{}".format(
            len(stgs), tot, stg))
        exp_srt_s = time.time()
        try:
            maybe(lambda flw_stgs_=flw_stgs: common.iperf3(flw_stgs_))
            stgs = stgs[:-1]
        except:
            print("Error: {}".format(sys.exc_info()[0]))
        print("Experiment duration: {:.2f} seconds".format(
            time.time() - exp_srt_s))

    maybe(common.finishExperiment)
    print("Total experiment duration: {:.2f} seconds".format(
        time.time() - tot_srt_s))


if __name__ == "__main__":
    main()
