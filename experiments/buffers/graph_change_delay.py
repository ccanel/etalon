#!/usr/bin/env python

import argparse
from os import path

from matplotlib import pyplot as plt


FONTSIZE = 15
MARKERS = ["o", "s", "D"]


def main():
    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        description="Parse log files generated by parse_change_delay.py")
    parser.add_argument(
        "--exp-file", help="The experiment output file.", required=True,
        type=str)
    parser.add_argument(
        "--out-dir", help="The path to the output directory.",
        required=True, type=str)
    args = parser.parse_args()

    data = []
    for toks in [lin.split(",") for lin  in open(args.exp_file, "r")][1:]:
        data.append({
            "ts_s": int(toks[0]),
            "nw_switch_us": int(toks[1]),
            "bw_gbps": float(toks[2]),
            "short_delay_us": float(toks[3]),
            "long_delay_us": float(toks[4]),
            "small_queue_cap": int(toks[5]),
            "big_queue_cap": int(toks[6]),
            "in_advance_us": int(toks[7]),
            "par": int(toks[8]),
            "secs": float(toks[9]),
            "byts": int(toks[10]),
            "bps": float(toks[11])
        })

    get_all = lambda key: sorted(list(set([d[key] for d in data])))
    delay_uss = get_all("short_delay_us")
    queue_caps = get_all("small_queue_cap")
    pars = get_all("par")

    # Figure out the maximum x and y values so that we can keep all of the
    # dimensions the same to make it easier to compare across graphs.
    all_xs = get_all("nw_switch_us")
    xmin = min(all_xs)
    xmax = max(all_xs)
    ymin = 0
    ymax = max(get_all("secs")) * 1.1

    for delay_us in delay_uss:
        for par in pars:
            plt.figure(figsize=(6, 4))
            # Plot each number of flows as a different line.
            for i, queue_cap in enumerate(queue_caps):
                # Select only the results with this delay, queue capacity, and
                # parallel flows. Pick the network switch period as the x value
                # and the flow completion time as the y value. Then, split the
                # (x, y) pairs into a list of xs and a list of ys.
                xs, ys = zip(*sorted(
                    [(d["nw_switch_us"], d["secs"]) for d in data
                     if (d["short_delay_us"] == delay_us and
                         d["small_queue_cap"] == queue_cap and
                         d["par"] == par)]))
                plt.plot(xs, ys, marker=MARKERS[i])
            plt.xscale("log")
            plt.legend(
                ["{} packets".format(queue_cap) for queue_cap in queue_caps],
                fontsize=FONTSIZE)
            plt.xlabel("Network switch period (s)", fontsize=FONTSIZE)
            plt.ylabel("Flow completion time (s)", fontsize=FONTSIZE)
            plt.xticks(fontsize=FONTSIZE)
            plt.yticks(fontsize=FONTSIZE)
            plt.xlim((xmin, xmax))
            plt.ylim((ymin, ymax))
            plt.tight_layout()
            plt.savefig(path.join(
                args.out_dir, "{}us_{}flows.pdf".format(delay_us, par)))
            plt.close()


if __name__ == "__main__":
    main()
