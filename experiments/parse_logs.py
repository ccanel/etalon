#!/usr/bin/env python

import collections
import glob
from os import path
import socket
from struct import unpack
import sys
# Directory containing this program.
PROGDIR = path.dirname(path.realpath(__file__))
# For python_config.
sys.path.insert(0, path.join(PROGDIR, "..", "etc"))

import numpy as np

import python_config

PERCENTILES = [25, 50, 75, 99, 99.9, 99.99, 99.999, 100]
RTT = python_config.CIRCUIT_LATENCY_s_TDF * 2
DURATION = 4300
# 1/1000 seconds.
BIN_SIZE_MS = 1


def parse_flowgrind_config(fn):
    flows = collections.defaultdict(list)
    sizes = {}
    for l in open(fn.split(".txt")[0] + ".config.txt"):
        l = l.split("-F")[1:]
        for x in l:
            hid = int(x.strip().split()[0])
            byts = int(x.strip().split("-Gs=q:C:")[1].split()[0])
            sizes[hid] = byts
    for l in open(fn):
        if "seed" in l:
            hid = int(l[4:].strip().split()[0])
            rack = int(l.split("/")[0].split()[-1].split(".")[2])
            flows[hid].append(rack)
            if l.split(":")[0][-1] == "S":
                time = float(l.split("duration = ")[1].split("/")[0]) * 1000000
                tp = float(l.split("through = ")[1].split("/")[0]) / 1000.
            else:
                flows[hid].append(time)
                flows[hid].append(tp)
                flows[hid].append(sizes[hid])

    for f in flows.keys():
        if flows[f][3] == float("inf"):
            del flows[f]
    tps = [f[3] for f in flows.values()]
    durs = [f[2] for f in flows.values()]
    byts = [f[4] for f in flows.values()]

    print len(tps), len(durs), len(byts)

    return tps, durs, byts


def msg_from_file(filename, chunksize=112):
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(chunksize)
            if chunk:
                yield chunk
            else:
                break


def get_seq_data(fn):
    print("Parsing: {}".format(fn))
    circuit_starts = collections.defaultdict(list)
    circuit_ends = collections.defaultdict(list)
    flows = collections.defaultdict(list)
    seen = collections.defaultdict(list)
    for msg in msg_from_file(fn):
        # type (int), timestamp (char[32]), latency (int), src (int), dst (int),
        # data (char[64])
        (t, ts, _, src, dst, data) = unpack("i32siii64s", msg)
        ip_bytes = unpack("!H", data[2:4])[0]
        sender = socket.inet_ntoa(data[12:16])
        recv = socket.inet_ntoa(data[16:20])
        proto = ord(data[9])
        ihl = (ord(data[0]) & 0xF) * 4
        sport = 0
        dport = 0
        seq = 0
        thl = 0
        if proto == 6:  # TCP
            sport = unpack("!H", data[ihl:ihl+2])[0]
            dport = unpack("!H", data[ihl+2:ihl+4])[0]
            seq = unpack("!I", data[ihl+4:ihl+8])[0]
            thl = (ord(data[ihl+12]) >> 4) * 4
        byts = ip_bytes - ihl - thl

        i = 0
        for a in xrange(len(ts)):
            if ord(ts[a]) == 0:
                break
            i += 1
        ts = float(ts[:i]) / python_config.TDF

        if t == 1 or t == 2:  # starting or closing
            sr = (src, dst)
            if t == 1:  # starting
                circuit_starts[sr].append(ts)
            if t == 2:  # closing
                if not circuit_starts[sr]:
                    continue
                circuit_ends[sr].append(ts)
            continue

        flow = (sender, recv, proto, sport, dport)
        if not flows[flow]:
            flows[flow].append((ts, seq, byts))
        else:
            last_ts, last_seq, last_bytes = flows[flow][-1]
            if abs(last_seq + last_bytes - seq) < 2:
                updated = True
                while updated:
                    updated = False
                    for prev_seen in seen[flow]:
                        prev_seq = prev_seen[1]
                        prev_bytes = prev_seen[2]
                        if abs(seq + byts - prev_seq) < 2:
                            seq = prev_seq
                            byts = prev_bytes
                            seen[flow].remove(prev_seen)
                            updated = True
                            break
                flows[flow].append((ts, seq, byts))
            else:
                seen[flow].append((ts, seq, byts))

    day_lens = []
    week_lens = []
    starts = []
    ends = []
    next_starts = []
    next_ends = []
    next_next_starts = []
    next_next_ends = []
    sr = (1, 2)
    for i in xrange(1, len(circuit_starts[sr])-2):
        prev_end = circuit_ends[sr][i-1]
        curr = circuit_starts[sr][i]
        curr_end = circuit_ends[sr][i]
        nxt = circuit_starts[sr][i+1]
        if i+1 >= len(circuit_ends[sr]):
            continue
        next_end = circuit_ends[sr][i+1]
        next_next = circuit_starts[sr][i+2]
        if i+2 >= len(circuit_ends[sr]):
            continue
        next_next_end = circuit_ends[sr][i+2]
        day_lens.append((curr_end - curr)*1e6)
        week_lens.append((nxt - curr)*1e6)
        starts.append((curr - prev_end)*1e6)
        ends.append((curr_end - prev_end)*1e6)
        next_starts.append((nxt - prev_end)*1e6)
        next_ends.append((next_end - prev_end)*1e6)
        next_next_starts.append((next_next - prev_end)*1e6)
        next_next_ends.append((next_next_end - prev_end)*1e6)
    out_start = np.average(starts[5:-5])
    out_end = np.average(ends[5:-5])
    out_next_start = np.average(next_starts[5:-5])
    out_next_end = np.average(next_ends[5:-5])
    out_next_next_start = np.average(next_next_starts[5:-5])
    out_next_next_end = np.average(next_next_ends[5:-5])
    day_lens = day_lens[5:-5]
    week_lens = week_lens[5:-5]
    print "circuit day avg and std dev", np.average(day_lens), np.std(day_lens)
    print "week avg and std dev", np.average(week_lens), np.std(week_lens)
    print out_start, out_end, out_next_start, out_next_end

    if len(circuit_starts[sr]) < 50:
        ts_start = flows.values()[0][0][0]
        ts_end = flows.values()[0][-1][0]
        for f in flows:
            fstart = flows[f][0][0]
            fend = flows[f][-1][0]
            if fstart < ts_start:
                ts_start = fstart
            if fend > ts_end:
                ts_end = fend
        circuit_starts[sr] = np.arange(ts_start - 0.002,
                                       ts_end + 0.002, 0.002)
        circuit_ends[sr] = np.arange(ts_start, ts_end + 0.004, 0.002)

    print("Found {} flows".format(len(flows)))
    results = {}
    for f in flows.keys():
        if "10.1.2." in f[0]:
            continue
        print("Parsing flow: {}".format(f))

        # Interpolated chunks for this flow.
        chunks_interp = []
        # Original (uninterpolated) chunks for this flow.
        chunks_orig = []
        last = 0
        print "Circuit starts: {}".format(len(circuit_starts[sr]))
        bad_windows = 0
        first_ts = flows[f][0][0]
        last_ts = flows[f][-1][0]
        for i in xrange(1, len(circuit_starts[sr])-2):
            prev_end = circuit_ends[sr][i-1]
            curr = circuit_starts[sr][i]
            curr_end = circuit_ends[sr][i]
            if curr_end < first_ts:
                continue
            if curr > last_ts:
                continue
            nxt = circuit_starts[sr][i+1]
            if i+1 >= len(circuit_ends[sr]):
                continue
            next_end = circuit_ends[sr][i+1]
            next_next = circuit_starts[sr][i+2]
            if i+2 >= len(circuit_ends[sr]):
                continue
            next_next_end = circuit_ends[sr][i+2]
            # A list of pairs where the first element is a relative timestamp
            # and the second element is a relative sequence number.
            out = []
            first = -1
            timing_offset = 30e-6
            for a in xrange(last, len(flows[f])):
                (ts, seq, _) = flows[f][a]
                if ts > next_next_end + timing_offset:
                    break
                if ts >= prev_end + timing_offset:
                    if first == -1:
                        first = seq

                    rel_ts = (ts - prev_end - timing_offset) * 1e6
                    rel_seq = seq - first
                    if out and rel_ts == out[-1][0]:
                        # print("i: {}".format(i))
                        # print("rel_ts: {}".format(rel_ts))
                        # print("ts: {}".format(ts))
                        # print("prev_end: {}".format(prev_end))
                        # print("timing_offset: {}".format(timing_offset))
                        # print("rel_seq: {}".format(rel_seq))
                        # print("seq: {}".format(seq))
                        # print("first: {}".format(first))
                        # Do not add this result if there already exists a value
                        # for this timestamp.
                        print(("Warning: Dropping ({}, {}) because we already "
                               "have data for that timestamp!").format(
                                   rel_ts, rel_seq))
                        continue

                    out.append((rel_ts, rel_seq))
                if ts < curr_end + timing_offset:
                    last = a
            if not out:
                bad_windows += 1
                out = [(0, 0), (DURATION, 0)]
            wraparound = False
            for ts, seq in out:
                if seq < -1e8 or seq > 1e8:
                    wraparound = True
            if not wraparound:
                # Sort the data so that it can be used by numpy.interp().
                out = sorted(out, key=lambda a: a[0])
                xs, ys = zip(*out)
                diffs = np.diff(xs) > 0
                if not np.all(diffs):
                    print("diffs: {}".format(diffs))
                    print("out:")
                    for x, y in out:
                        print("  {}: {}".format(x, y))
                    raise Exception(
                        "numpy.interp() requires x values to be increasing")
                # Interpolate based on the data that we have.
                chunks_interp.append(np.interp(xrange(DURATION), xs, ys))

                # Also record the original (uninterpolated) chunk data.
                chunks_orig.append((xs, ys))

        # List of lists, where each sublist corresponds to one timestep and each
        # entry of each sublist corresponds to a sequence number for that
        # timestep.
        unzipped = zip(*chunks_interp)
        # Average the sequence numbers for across each timestep, creating the
        # final results for this flow.
        results[f] = (
            [np.average(tstamp_results) for tstamp_results in unzipped],
            chunks_orig)

        print("Chunks for this flow: {}".format(len(chunks_interp)))
        print("Timestamps for this flow: {}".format(len(unzipped)))
        print("Bad windows for this flow: {}".format(bad_windows))

    old_len = len(results)
    # Remove flows that have no datapoints.
    results = {flw: flw_res for flw, flw_res in results.items() if flw_res[0]}
    len_delta = old_len - len(results)
    if len_delta:
        print("Warning: {} flows were filtered out!".format(len_delta))

    print("Flows for which we have results:")
    for k in results.keys():
        print("\t{}".format(k))

    # Extract the chunk results.
    chunks_orig_all = {
        flw: chunks_orig for flw, (_, chunks_orig) in results.items()}
    # Turn a list of lists of results for each flow into a list of lists of
    # results for all flows at one timestep.
    unzipped = zip(*[r for r, _ in results.values()])
    # Average the results of all flows at each timestep. So, the output is
    # really: For each timestep, what's the average sequence number of all
    # flows.
    results = [np.average(q) for q in unzipped]
    return results, (out_start, out_end, out_next_start,
                     out_next_end, out_next_next_start,
                     out_next_next_end), chunks_orig_all


def parse_packet_log(fn):
    print("Parsing: {}".format(fn))
    latencies = []
    latencies_circuit = []
    latencies_packet = []
    throughputs = collections.defaultdict(int)
    circuit_bytes = collections.defaultdict(int)
    packet_bytes = collections.defaultdict(int)
    flow_start = {}
    flow_end = {}
    number_circuit_ups = collections.defaultdict(int)
    circuit_starts = collections.defaultdict(list)
    most_recent_circuit_up = collections.defaultdict(int)
    bytes_in_rtt = collections.defaultdict(lambda: collections.defaultdict(int))
    for msg in msg_from_file(fn):
        (t, ts, lat, src, dst, data) = unpack("i32siii64s", msg)
        byts = unpack("!H", data[2:4])[0]
        circuit = ord(data[1]) & 0x1
        sender = ord(data[14])
        recv = ord(data[18])
        i = 0
        for a in xrange(len(ts)):
            if ord(ts[a]) == 0:
                break
            i += 1
        ts = float(ts[:i])
        if t == 1 or t == 2:  # starting or closing
            sr = (src, dst)
            if t == 1:  # starting
                most_recent_circuit_up[sr] = ts
            if t == 2:  # closing
                circuit_starts[sr].append(ts / python_config.TDF)
                number_circuit_ups[sr] += 1
            continue

        latency = float(lat)
        sr = (sender, recv)
        if byts < 100:
            continue
        if sr not in flow_start:
            flow_start[sr] = ts / python_config.TDF

        if circuit:
            which_rtt = int((ts - most_recent_circuit_up[sr] - 0.5 * RTT) / RTT)
            bytes_in_rtt[sr][which_rtt] += byts
            circuit_bytes[sr] += byts
        else:
            packet_bytes[sr] += byts

        throughputs[sr] += byts
        flow_end[sr] = ts / python_config.TDF
        if byts > 1000:
            latencies.append(latency)
            if circuit:
                latencies_circuit.append(latency)
            else:
                latencies_packet.append(latency)
    lat = zip(PERCENTILES, map(lambda x: np.percentile(latencies, x),
                               PERCENTILES))
    latc = [(p, 0) for p in PERCENTILES]
    if latencies_circuit:
        latc = zip(PERCENTILES, map(lambda x: np.percentile(
            latencies_circuit, x), PERCENTILES))
    latp = zip(PERCENTILES, map(lambda x: np.percentile(latencies_packet, x),
                                PERCENTILES))
    tp = {}
    b = collections.defaultdict(dict)
    p = {}
    c = {}
    for sr in flow_start:
        total_time = flow_end[sr] - flow_start[sr]
        tp[sr] = throughputs[sr] / total_time
        tp[sr] *= 8  # bytes to bits
        tp[sr] /= 1e9  # bits to gbits

        p[sr] = (packet_bytes[sr] / total_time) * 8 / 1e9
        c[sr] = (circuit_bytes[sr] / total_time) * 8 / 1e9

        n = 0
        for ts in circuit_starts[sr]:
            if ts >= flow_start[sr] and ts <= flow_end[sr]:
                n += 1
        max_bytes = n * RTT * (python_config.CIRCUIT_BW_Gbps_TDF * 1e9 / 8.)
        for i, r in sorted(bytes_in_rtt[sr].items()):
            b[sr][i] = (r / max_bytes) * 100

    return tp, (lat, latc, latp), p, c, b, \
        sum(circuit_bytes.values()), sum(packet_bytes.values())


def parse_validation_log(fn, dur_ms=1300, bin_size_ms=1):
    print("Parsing: {}".format(fn))
    # Map of flow ID to pair (src rack, dst rack).
    id_to_sr = {}
    with open(fn.strip(".txt") + ".config.txt") as f:
        for line in f:
            line = line.split("-F")[1:]
            for flow_cnf in line:
                flow_cnf = flow_cnf.strip()
                idx = int(flow_cnf.split()[0])
                # Extract src rack id.
                s = int(flow_cnf.split("-Hs=10.1.")[1].split(".")[0])
                # Extract dst rack id.
                r = int(flow_cnf.split(",d=10.1.")[1].split(".")[0])
                id_to_sr[idx] = (s, r)

    # Map of pair (src rack, dst rack) to a map of window *start* timestamp to
    # the number of bytes sent during the window beginning with this timestamp.
    sr_to_tstamps = collections.defaultdict(
        lambda: collections.defaultdict(int))
    # Map of emulated src idx (i.e., flow idx) to a map of window *end*
    # timestamp to the src's CWND at the timestamp (i.e., at the time that the
    # window ended).
    flow_to_cwnds = collections.defaultdict(
        lambda: collections.defaultdict(int))
    with open(fn) as f:
        for line in f:
            # Ignore comment lines, empty lines, and "D" lines.
            if line[0] == "S":
                line = line[1:].strip()
                splits = line.split()
                # Flow ID.
                idx = int(splits[0])
                # Start timestamp for this window.
                ts_s_start = float(splits[1])
                # End timestamp for this window.
                ts_s_end = float(splits[2])
                # Throughput for this window.
                curr_tput_mbps = float(splits[3])
                # Bits sent during this window. Mb/s -> b. Do not divide by TDF.
                curr_b = curr_tput_mbps * 1e6  * (ts_s_end - ts_s_start)
                # Record the bytes sent during this window.
                sr_to_tstamps[id_to_sr[idx]][ts_s_start] += curr_b
                # CWND at the end of this window.
                cwnd = int(splits[11])
                # Record this flow's cwnd at the end of this window.
                flow_to_cwnds[idx][ts_s_end] = cwnd
    # For each (src, dst) rack pair, transform the mapping from timestamp to
    # bytes into a list of sorted pairs of (timestamp, bytes).
    sr_to_tstamps = {sr: sorted(tstamps.items())
                     for sr, tstamps in sr_to_tstamps.items()}
    # For each flow, transform the mapping from timestamp to cwnd into a list of
    # sorted pairs of (timestamp, cwnd).
    flow_to_cwnds = {flw: sorted(cwnds.items())
                     for flw, cwnds in flow_to_cwnds.items()}

    # Map of pair (src rack, dst rack) to list of throughputs in Gb/s. Each
    # throughput corresponds to the throughput during one bin.
    sr_to_tputs = collections.defaultdict(list)
    for sr, tstamps in sr_to_tstamps.items():
        for win_start_ms in xrange(0, dur_ms, bin_size_ms):
            win_start_s = win_start_ms / 1e3
            win_end_s = win_start_s + (bin_size_ms / 1e3)
            # Find all the logs (i.e., numbers of bytes during some window) for
            # the current bin...
            cur_samples = [b for ts_s, b in tstamps
                           # E.g., for i = 1 and BIN_SIZE_MS = 1, if timestamp
                           # is between 1 ms and 2 ms.
                           if win_start_s <= ts_s < win_end_s]
            # ...and sum them up to calculate the total number of bytes sent in
            # this bin (e.g., if the bin size is 1, then this is the total
            # amount of bytes sent in 1 ms).
            cur_b = sum(cur_samples)
            gbps = cur_b * (1 / BIN_SIZE_MS) * 1e3 / 1e9
            sr_to_tputs[sr].append((win_start_ms / 1e3, gbps))

    means = {}
    stdevs = {}
    for sr, tputs in sr_to_tputs.items():
        # Jump over data from before the flows started.
        start_idx = 0
        for _, tput in tputs:
            if round(tput) > 0:
                break
            start_idx += 1
        # Extract the tputs from of list of pairs of (window start time, tput).
        _, tputs = zip(*tputs[start_idx:])
        means[sr] = np.mean(tputs)
        stdevs[sr] = np.std(tputs)

    print("Num tput logs:")
    for sr, tputs in sr_to_tputs.items():
        print("  (src rack, dst rack): {} = {}".format(sr, len(tputs)))
    print("Means:")
    for sr, mean in means.items():
        print("  (src rack, dst rack): {} = {} Gb/s".format(sr, mean))
    print("Standard deviations:")
    for sr, stdev in stdevs.items():
        print("  (src rack, dst rack): {} = {} Gb/s".format(sr, stdev))
    print("Mean of means: {} Gb/s".format(np.mean(means.values())))
    print(
        "Mean of standard deviations: {} Gb/s".format(np.mean(stdevs.values())))

    return sr_to_tputs, flow_to_cwnds


def parse_hdfs_logs(folder):
    data = []
    durations = []

    fn = folder + "/*-logs/hadoop*-datanode*.log"
    print fn
    logs = glob.glob(fn)

    for log in logs:
        for line in open(log):
            if "clienttrace" in line and "HDFS_WRITE" in line:
                byts = int(line.split("bytes: ")[1].split()[0][:-1])
                if byts > 1024 * 1024 * 99:
                    duration = ((float(line.split(
                        "duration(ns): ")[1].split()[0]) * 1e-6) /
                                python_config.TDF)
                    data.append((byts / 1024. / 1024., duration))

    durations = sorted(zip(*data)[1])
    return durations


def parse_hdfs_throughput(folder):
    fn = folder + "/report/dfsioe/hadoop/bench.log"
    logs = glob.glob(fn)

    for log in logs:
        for line in open(log):
            if "Number of files" in line:
                num_files = int(line.split("files: ")[1])
            if "Throughput mb/sec:" in line:
                # divide by number of replicas
                return (float(line.split("mb/sec:")[1]) *
                        num_files * 8 / 1024.) * python_config.TDF / 2.
