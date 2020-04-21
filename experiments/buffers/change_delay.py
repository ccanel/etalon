#!/usr/bin/env python

from os import path
import signal
import sys
# Directory containing this program.
PROGDIR = path.dirname(path.realpath(__file__))
# For click_common and common.
sys.path.insert(0, path.join(PROGDIR, ".."))
# For python_config.
sys.path.insert(0, path.join(PROGDIR, "..", "..", "etc"))
import time
import traceback

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
# Bandwidth for all links.
BW_Gbps = 5.5

# # Long sweep settings.
# BASE_DELAYS_US = [100, 200, 500, 1000]
# QUEUE_CAPS = [50, 100, 200, 400]
# NW_SWITCH_POW_MIN = 12
# NW_SWITCH_POW_MAX = 40
# NW_SWITCH_USs = [
#     2 ** (nw_switch_pow / 2.)
#     for nw_switch_pow in xrange(NW_SWITCH_POW_MIN, NW_SWITCH_POW_MAX + 1)]
# PARS = [1, 5, 10, 20]
# SCALING_FACTOR = 5.

# Short sweep settings.
BASE_DELAYS_US = [100, 500, 1000]
QUEUE_CAPS = [100, 200, 400]
NW_SWITCH_POW_MIN = 6
NW_SWITCH_POW_MAX = 20
NW_SWITCH_USs = [
    2 ** nw_switch_pow
    for nw_switch_pow in xrange(NW_SWITCH_POW_MIN, NW_SWITCH_POW_MAX + 1)]
PARS = [5, 10, 20]
SCALING_FACTOR = 5.

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


# From: https://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish
class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise RuntimeError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, typ, value, tracebck):
        signal.alarm(0)


def maybe(fnc, do=not DRY_RUN):
    """ Executes "fnc" if "do" is True, otherwise does nothing. """
    if do:
        fnc()


def main():
    # Convenience functions.
    tdf = lambda val: val * python_config.TDF
    intify = lambda val: int(round(val))
    # Assemble settings. Generate the list of settings first so that we know the
    # total number of experiments.
    stgs = sorted([
        (
            {
                "type": "fixed",
                "fixed_schedule": (
                    "4 "
                    # "{nw_switch_us} {config_long_lat} "
                    "{nw_switch_us} {config_short_lat} "
                    "0 {config_night} "
                    "{nw_switch_us} {config_long_lat} "
                    # "{nw_switch_us} {config_short_lat} "
                    "0 {config_night}"
                ).format(
                    # Disable network.
                    config_night=("-1/" * python_config.NUM_RACKS)[:-1],
                    # The short (circuit) and long (packet) paths will be active
                    # for the same duration.
                    nw_switch_us=nw_switch_us,
                    config_short_lat="".join([
                        "{}/".format((rack + 1) % python_config.NUM_RACKS)
                        for rack in xrange(python_config.NUM_RACKS)])[:-1],
                    config_long_lat="".join([
                        "{}/".format((rack + 2) % python_config.NUM_RACKS)
                        for rack in xrange(python_config.NUM_RACKS)])[:-1],
                ),
                "small_queue_cap": queue_cap,
                "big_queue_cap": intify(queue_cap * SCALING_FACTOR),
                "circuit_lat_s": tdf(delay_us / 1e6),
                # Divide by 2 because the packet path has two links that will
                # each receive the same delay.
                "packet_lat_s": tdf((delay_us * SCALING_FACTOR) / 1e6 / 2.),
                "circuit_bw_Gbps": BW_Gbps,
                "packet_bw_Gbps": BW_Gbps,
                "queue_resize": True,
                "in_advance": intify(tdf(min(
                    0.75 * nw_switch_us, delay_us * (SCALING_FACTOR - 1)))),
                "packet_log": PACKET_LOG,
                "cc": CC,
                # Add the network switch period and number of parallel flows to
                # the filename.
                "details": "{}-{}".format(intify(nw_switch_us), par)
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
        for par in PARS])
    # Total number of experiments.
    tot = len(stgs)
    tot_srt_s = time.time()
    while stgs:
        # The iperf3 integration is very fragile and prone to transient errors.
        # This loop will retry an experiment until it succeeds.

        # Use the first experiment's CC mode to avoid unnecessarily restarting
        # the cluster.
        maybe(lambda: common.initializeExperiment(
            "iperf3", cc=stgs[0][0]["cc"], sync=SYNC))

        while stgs:
            stg = stgs[-1]
            cnf, flw_stgs = stg

            maybe(lambda cnf_=cnf: click_common.setConfig(cnf_))
            print("--- {} of {} experiments remaining, config:\n{}".format(
                len(stgs), tot, stg))
            exp_srt_s = time.time()
            try:
                #with timeout(seconds=120):
                maybe(lambda flw_stgs_=flw_stgs: common.iperf3(flw_stgs_))
                print("Experiment duration: {:.2f} seconds".format(
                    time.time() - exp_srt_s))
                stgs = stgs[:-1]
            except:
                traceback.print_exc()
                maybe(common.finishExperiment)
                print("Restarting cluster...")
                time.sleep(10)
                break

    maybe(common.finishExperiment)
    print("Total experiment duration: {:.2f} seconds".format(
        time.time() - tot_srt_s))


if __name__ == "__main__":
    main()
