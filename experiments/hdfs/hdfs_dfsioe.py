#!/usr/bin/env python

import sys
sys.path.insert(0, '/etalon/experiments')
from common import initializeExperiment, finishExperiment, dfsioe
from click_common import setConfig

CONFIGS = [
    {'type': 'normal', 'traffic_source': 'QUEUE'},
    {'type': 'resize', 'traffic_source': 'QUEUE', 'in_advance': 20000},
    {'type': 'resize', 'traffic_source': 'QUEUE', 'in_advance': 20000, 'cc': 'retcp'},
]

for c in CONFIGS:
    c['packet_log'] = False
    if c['type'] == 'resize':
        c['type'] = 'normal'
        c['queue_resize'] = True
    else:
        c['queue_resize'] = False
    if 'cc' not in c:
        c['cc'] = 'reno'
    c['thresh'] = 8000

for h in ['HDFS', 'reHDFS']:
    for c in CONFIGS:
        c['hdfs'] = h
        print '--- running %s, %s, %s, %s' % (h, c['traffic_source'],
                                              c['queue_resize'], c['cc'])
        if c['traffic_source'] == 'ADU':
            initializeExperiment(h + "_adu")
        else:
            initializeExperiment(h)
        setConfig(c)
        print '--- done initializing...'
        dfsioe('h21', h)

finishExperiment()
