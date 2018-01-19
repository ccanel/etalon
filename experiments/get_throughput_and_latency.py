#!/usr/bin/env python

import sys
import glob
import numpy as np

from collections import defaultdict

percentiles = [25, 50, 75, 99, 99.9, 99.99, 99.999, 100]
RTT = 0.001200
CIRCUIT_BW = 4  # without TDF


def get_tput_and_dur(fn):
    flows = defaultdict(list)
    sizes = {}
    for l in open(fn.split('.txt')[0] + '.config.txt'):
        l = l.split('-F')[1:]
        for x in l:
            id = int(x.strip().split()[0])
            bytes = int(x.strip().split('-Gs=q:C:')[1].split()[0])
            sizes[id] = bytes
    for l in open(fn):
        if 'seed' in l:
            id = int(l[4:].strip().split()[0])
            rack = int(l.split('/')[0].split()[-1].split('.')[2])
            flows[id].append(rack)
            if l.split(":")[0][-1] == 'S':
                time = float(l.split('duration = ')[1].split('/')[0]) * 1000000
                tp = float(l.split('through = ')[1].split('/')[0]) / 1000.0
            else:
                flows[id].append(time)
                flows[id].append(tp)
                flows[id].append(sizes[id])

    for f in flows.keys():
        if flows[f][3] == float('inf'):
            del flows[f]
    tps = [f[3] for f in flows.values()]
    durs = [f[2] for f in flows.values()]
    bytes = [f[4] for f in flows.values()]

    print len(tps), len(durs), len(bytes)

    return tps, durs, bytes


def get_tput_and_lat(fn):
    latencies = []
    latencies_circuit = []
    latencies_packet = []
    throughputs = defaultdict(int)
    circuit_bytes = defaultdict(int)
    packet_bytes = defaultdict(int)
    flow_start = {}
    flow_end = {}
    number_circuit_ups = defaultdict(int)
    circuit_starts = defaultdict(list)
    most_recent_circuit_up = defaultdict(int)
    bytes_in_rtt = defaultdict(lambda: defaultdict(int))
    for l in open(fn):
        ts, d = l.split(':')
        ts = float(ts)

        if 'starting' in d or 'closing' in d:
            src = int(d.split('->')[0].strip().split(' ')[-1])
            dst = int(d.split('->')[1])
            sr = (src, dst)
            if 'starting' in d:
                most_recent_circuit_up[sr] = ts
            if 'closing' in d:
                circuit_starts[sr].append(ts / 20.0)
                number_circuit_ups[sr] += 1
            continue

        d = d.split(',')
        bytes = int(d[0].split('(')[1].split(' ')[0])
        sender = int(d[0].split('->')[0])
        recv = int(d[0].split('->')[1].split('(')[0])
        latency = float(d[-1].split(' ')[-1].split('us')[0])
        sr = (sender, recv)
        if bytes < 100:
            continue
        if sr not in flow_start:
            flow_start[sr] = ts / 20.0  # TDF

        circuit = (d[1].strip() == 'circuit')
        if circuit:
            which_rtt = int((ts - most_recent_circuit_up[sr]) / RTT)
            bytes_in_rtt[sr][which_rtt] += bytes
            circuit_bytes[sr] += bytes
        else:
            packet_bytes[sr] += bytes

        throughputs[sr] += bytes
        flow_end[sr] = ts / 20.0  # TDF
        if bytes > 1000:
            latencies.append(latency)
            if circuit:
                latencies_circuit.append(latency)
            else:
                latencies_packet.append(latency)
    lat = zip(percentiles, map(lambda x: np.percentile(latencies, x),
                               percentiles))
    latc = zip(percentiles, map(lambda x: np.percentile(latencies_circuit, x),
                                percentiles))
    latp = zip(percentiles, map(lambda x: np.percentile(latencies_packet, x),
                                percentiles))
    tp = {}
    b = defaultdict(dict)
    p = {}
    c = {}
    for sr in flow_start:
        total_time = flow_end[sr] - flow_start[sr]
        tp[sr] = throughputs[sr] / total_time
        tp[sr] *= 8  # bytes to bits
        tp[sr] /= 1000000000  # bits to gbits

        p[sr] = (packet_bytes[sr] / total_time) * 8 / 10**9
        c[sr] = (circuit_bytes[sr] / total_time) * 8 / 10**9

        n = 0
        for ts in circuit_starts[sr]:
            if ts >= flow_start[sr] and ts <= flow_end[sr]:
                n += 1
        print n, number_circuit_ups[sr]
        max_bytes = n * RTT * (CIRCUIT_BW * 10**9 / 8.0)
        for i, r in sorted(bytes_in_rtt[sr].items()):
            b[sr][i] = (r / max_bytes) * 100

    print
    print fn
    print tp
    print lat
    print sorted(b.items())
    print p
    print c
    return tp, (lat, latc, latp), p, c, b, \
        sum(circuit_bytes.values()), sum(packet_bytes.values())

if __name__ == "__main__":
    fns = sys.argv[1]
    if 'tmp' not in fns:
        fns += '/tmp/*'
    for fn in glob.glob(fns):
        get_tput_and_lat(fn)