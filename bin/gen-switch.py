#!/usr/bin/env PYTHONPATH=../etc/ python

from python_config import *

print 'define($DEVNAME %s)' % DATA_EXT_IF
print 'define($NUM_RACKS %s)' % NUM_RACKS
print

k = 0
ip_def = 'define('
for i in xrange(1, NUM_RACKS+1):
    ip_def += '$IP%d 10.%d.10.%d, ' % (i, DATA_NET, i)
    for j in xrange(1, HOSTS_PER_RACK+1):
        ip_str = '$IP%d%d' % (i, j)
        ip = '10.%d.%d.%d' % (DATA_NET, i, j)
        ip_def += '%s %s, ' % (ip_str, ip)
        k += 1
        if k == 4:
            ip_def = ip_def[:-1]
            ip_def += '\n       '
            k = 0
ip_def = ip_def.strip()[:-1] + ')'

print ip_def
print

print 'define ($CIRCUIT_BW %.1fGbps, $PACKET_BW %.1fGbps)' % (
    CIRCUIT_BW_BY_TDF, PACKET_BW_BY_TDF)
print

print 'define ($PACKET_LATENCY %s)' % PACKET_LATENCY
print 'define ($CIRCUIT_LATENCY %s)' % CIRCUIT_LATENCY
print 'define ($BIG_BUFFER_SIZE %s, $SMALL_BUFFER_SIZE %s)' % (
    128, 16)
print

print 'define ($RECONFIG_DELAY %d)' % RECONFIG_DELAY
print 'define ($TDF %d)' % (int(TDF))
print

print 'StaticThreadSched(in 0,'
print '                  traffic_matrix 1,'
print '                  sol 2,'
print '                  runner 3,'
j = 4
k = 0
for i in xrange(1, NUM_RACKS+1):
    print '                  hybrid_switch/circuit_link%d %d,' % (i, j)
    k += 1
    j += 1
k = 0
for i in xrange(1, NUM_RACKS+1):
    print '                  hybrid_switch/packet_up_link%d %d,' % (i, j)
    k += 1
    if k == 4:
        j += 1
        k = 0
k = 0
for i in xrange(1, NUM_RACKS+1):
    print '                  hybrid_switch/ps/packet_link%d %d,' % (i, j)
    k += 1
    if k == 4:
        j += 1
        k = 0
print ')'
print

print 'ControlSocket("TCP", %d)' % (CONTROL_SOCKET_PORT)
print

print 'traffic_matrix :: EstimateTraffic($NUM_RACKS, SOURCE QUEUE)'
print 'sol :: Solstice($NUM_RACKS, $CIRCUIT_BW, $PACKET_BW, ' \
    '$RECONFIG_DELAY, $TDF)'
print 'runner :: RunSchedule($NUM_RACKS, RESIZE false)'
print

print 'in :: FromDPDKDevice(0)'
print 'out :: ToDPDKDevice(0)'
print

print 'arp_c :: Classifier(12/0800, 12/0806 20/0002, 12/0806 20/0001)'
print 'arp :: ARPQuerier($DEVNAME:ip, $DEVNAME:eth)'
print 'arp_r :: ARPResponder($DEVNAME)'
print

print 'elementclass in_classfy {'
print '  input[0] -> IPClassifier('
for i in xrange(1, NUM_RACKS+1):
    rack_str = '    src host $IP%d or ' % (i)
    k = 1
    for j in xrange(1, HOSTS_PER_RACK+1):
        rack_str += 'src host $IP%d%d or ' % (i, j)
        k += 1
        if k == 4:
            rack_str = rack_str[:-1]
            rack_str += '\n    '
    if i < NUM_RACKS:
        print rack_str[:-4] + ','
    else:
        print rack_str[:-4]
print '  )'
print '  => %soutput' % (str(list(xrange(NUM_RACKS))))
print '}'
print

print 'elementclass out_classfy {'
print '  input[0] -> IPClassifier('
for i in xrange(1, NUM_RACKS+1):
    rack_str = '    dst host $IP%d or ' % (i)
    k = 1
    for j in xrange(1, HOSTS_PER_RACK+1):
        rack_str += 'dst host $IP%d%d or ' % (i, j)
        k += 1
        if k == 4:
            rack_str = rack_str[:-1]
            rack_str += '\n    '
    if i < NUM_RACKS:
        print rack_str[:-4] + ','
    else:
        print rack_str[:-4]
print '  )'
print '  => %soutput' % (str(list(xrange(NUM_RACKS))))
print '}'
print

print 'elementclass packet_link {'
print '  input%s' % (str(list(xrange(NUM_RACKS))))
print '    => RoundRobinSched'
print '    -> lu :: LinkUnqueue($PACKET_LATENCY, $PACKET_BW)'
print '    -> output'
print '}'
print

print 'elementclass circuit_link {'
print '  input%s' % (str(list(xrange(NUM_RACKS))))
print '    => ps :: SimplePullSwitch(-1)'
print '    -> lu :: LinkUnqueue($CIRCUIT_LATENCY, $CIRCUIT_BW)'
print '    -> StoreData(1, 1) -> SetIPChecksum'
print '    -> output'
print '}'
print


print 'elementclass packet_switch {'
out_classfy = '  '
for i in xrange(1, NUM_RACKS+1):
    out_classfy += 'c%d, ' % i
print out_classfy[:-2] + ' :: out_classfy'
print

for i in xrange(1, NUM_RACKS+1):
    queues = '  '
    for j in xrange(1, NUM_RACKS+1):
        queues += 'q%d%d, ' % (i, j)
    queues = queues[:-1]
    if i < NUM_RACKS:
        print queues
    else:
        print queues[:-1]
print ' :: Queue(CAPACITY 3)'
print

pl = ''
k = 0
for i in xrange(1, NUM_RACKS+1):
    pl += 'packet_link%d, ' % i
    k += 1
    if k == 4:
        pl = pl[:-1]
        pl += '\n  '
        k = 0
pl = pl.strip()[:-1]
pl = '  ' + pl + ' :: packet_link'
print pl
print

for i in xrange(1, NUM_RACKS+1):
    input = '  input[%d] -> c%d => ' % (i-1, i)
    for j in xrange(1, NUM_RACKS+1):
        input += 'q%d%d, ' % (i, j)
    input = input[:-2]
    print input
print

for i in xrange(1, NUM_RACKS+1):
    output = '  '
    for j in xrange(1, NUM_RACKS+1):
        output += 'q%d%d, ' % (j, i)
    output = output[:-2]
    output += ' => packet_link%d -> [%d]output' % (i, i-1)
    print output
print

for i in xrange(1, NUM_RACKS+1):
    output = '  '
    for j in xrange(1, NUM_RACKS+1):
        output += 'q%d%d[1], ' % (i, j)
    output = output[:-2]
    output += ' -> [%d]output' % (i-1 + NUM_RACKS)
    print output

print '}'
print


print 'hybrid_switch :: {'

out_classfy = '  '
for i in xrange(1, NUM_RACKS+1):
    out_classfy += 'c%d, ' % i
print out_classfy[:-2] + ' :: out_classfy'
print

for i in xrange(1, NUM_RACKS+1):
    queues = '  '
    for j in xrange(1, NUM_RACKS+1):
        queues += 'q%d%d, ' % (i, j)
    queues = queues[:-1]
    if i < NUM_RACKS:
        print queues
    else:
        print queues[:-1]
print ' :: {'
print '      input[0] -> q :: LockQueue(CAPACITY $SMALL_BUFFER_SIZE)'
print '      input[1] -> lq :: Queue(CAPACITY 5)  // loss queue'
print '      lq, q => PrioSched -> output'
print ' }'
print

cl = ''
k = 0
for i in xrange(1, NUM_RACKS+1):
    cl += 'circuit_link%d, ' % i
    k += 1
    if k == 4:
        cl = cl[:-1]
        cl += '\n  '
        k = 0
cl = cl.strip()[:-1]
cl = '  ' + cl + ' :: circuit_link'
print cl
print

pl = ''
k = 0
for i in xrange(1, NUM_RACKS+1):
    pl += 'packet_up_link%d, ' % i
    k += 1
    if k == 4:
        pl = pl[:-1]
        pl += '\n  '
        k = 0
pl = pl.strip()[:-1]
pl = '  ' + pl + ' :: packet_link'
print pl
print

print '  ps :: packet_switch'
print

for i in xrange(1, NUM_RACKS+1):
    # Input port paint
    input = '  input[%d] -> Paint(%d, 20) -> c%d => ' % (i-1, i, i)
    for j in xrange(1, NUM_RACKS+1):
        input += 'q%d%d, ' % (i, j)
    input = input[:-2]
    print input
print

for i in xrange(1, NUM_RACKS+1):
    output = '  '
    for j in xrange(1, NUM_RACKS+1):
        output += 'q%d%d, ' % (j, i)
    output = output[:-2]
    # dest paint
    output += ' => circuit_link%d -> Paint(%d, 21) -> ' \
              '[%d]output' % (i, i, i-1)
    print output
print

for i in xrange(1, NUM_RACKS+1):
    for j in xrange(1, NUM_RACKS+1):
        print '  q%d%d -> pps%d%d :: SimplePullSwitch(0)' % (i, j, i, j)

for i in xrange(1, NUM_RACKS+1):
    output = '  '
    for j in xrange(1, NUM_RACKS+1):
        output += 'pps%d%d, ' % (i, j)
    output = output[:-2]
    # dest paint
    output += ' => packet_up_link%d -> [%d]ps[%d] -> ' \
              'Paint(%d, 21) -> [%d]output' % (i, i-1, i-1, i, i-1)
    print output
print

print '  // dropped PS packets -> loss queues'
for i in xrange(1, NUM_RACKS+1):
    output = '  ps[%d] -> out_classfy => ' % (i-1 + NUM_RACKS)
    for j in xrange(1, NUM_RACKS+1):
        output += '[1]q%d%d, ' % (i, j)
    output = output[:-2]
    print output

print '}'
print

print 'in -> arp_c -> MarkIPHeader(14) -> StripToNetworkHeader ' \
    '-> GetIPAddress(16)'
print '   -> pc :: IPClassifier(dst host $DEVNAME:ip icmp echo, -)[1]'
print '   -> divert_acks :: Switch(0)'
print '   -> st :: SetTimestamp(FIRST true)'
print '   -> in_classfy%s' % (str(list(xrange(NUM_RACKS))))
print '   => hybrid_switch%s' % (str(list(xrange(NUM_RACKS))))
print '   -> hsl :: HSLog($NUM_RACKS) -> ecem :: ECEMark($NUM_RACKS) -> ' \
    'arp -> out'
print
print 'divert_acks[1] ' \
    '-> acks :: IPClassifier(tcp ack and len < 100, -)[1] -> st'
print
print 'arp_c[1] -> [1]arp'
print 'arp_c[2] -> arp_r -> out'
print

print 'acks -> arp'
print 'pc -> ICMPPingResponder -> arp'