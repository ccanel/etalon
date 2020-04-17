#!/usr/bin/env python

import argparse
import json
import os
from os import path


def main():
    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        description="Parse log files generated by change_delay.py")
    parser.add_argument(
        "--exp-dir", help="The experiment output directory.", required=True,
        type=str)
    parser.add_argument(
        "--out-file", help="The path to the output file.",
        required=True, type=str)
    args = parser.parse_args()
    exp_dir = args.exp_dir

    # Extract duration, bytes sent, and data rate from each results JSON file.
    data = []
    for fln in os.listdir(exp_dir):
        if fln.endswith(".json"):
            # Parse experiment parameters.
            toks = fln[:-5].split("-")
            ts_s = int(toks[0])
            nw_switch_us = int(toks[-3])
            bw_gbps = float(toks[11])
            short_delay_us = float(toks[9]) * 1e6
            long_delay_us = float(toks[10]) * 1e6
            small_queue_cap = int(toks[3])
            big_queue_cap = int(toks[4])
            in_advance_us = int(toks[7])
            par = int(toks[-2])

            # Record results.
            with open(path.join(exp_dir, fln), "r") as fil:
                jsn = json.load(fil)
            res = jsn[0]["output"]["end"]["sum_received"]
            data.append((
                ts_s,
                nw_switch_us,
                bw_gbps,
                short_delay_us,
                long_delay_us,
                small_queue_cap,
                big_queue_cap,
                in_advance_us,
                par,
                float(res["seconds"]),
                int(res["bytes"]),
                float(res["bits_per_second"])))

    # Create output CSV file.
    with open(args.out_file, "w") as fil:
        fil.write((
            "experiment id,"
            "network switch period (us),"
            "bandwidth (Gbps),"
            "short path delay (us),"
            "long path delay (us),"
            "ToR queue small capacity (1500 byte packets),"
            "ToR queue big capacity (1500 byte packets),"
            "ToR prebuffering duration (us),"
            "parallel flows,"
            "flow duration (s),"
            "bytes received,"
            "flow rate (bps)\n"))
        for row in data:
            fil.write("{}\n".format(",".join([str(val) for val in row])))


if __name__ == "__main__":
    main()
