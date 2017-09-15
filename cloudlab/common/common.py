#!/usr/bin/python

import time
import threading
import sys
import os
import socket
import select
import paramiko
import rpyc
from subprocess import Popen, PIPE, STDOUT, call

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True

RPYC_PORT = 18861

NODES_FILE = os.path.expanduser('~/sdrt/cloudlab/common/handles.cloudlab')
MININET_NODES_FILE = os.path.expanduser('~/sdrt/cloudlab/common/mininet.cloudlab')

ADU_PRELOAD = os.path.expanduser('~/sdrt/sdrt-ctrl/lib/sdrt-ctrl.so')

RACKS = []
PHYSICAL_NODES = []
HANDLE_TO_IP = {}
NUM_RACKS = 0
HOSTS_PER_RACK = 0

TCP_IP = 'localhost'
TCP_PORT = 1239
BUFFER_SIZE = 1024
CLICK_SOCKET = None

MAX_CONCURRENT = 128

THREADS = []
THREADLOCK = threading.Lock()

IPERF3_CLIENT = 'iperf3 -p53%s -i0.1 -t1 -c %s'
PING = 'sudo ping -i0.05 -w1 %s'

##
## Experiment commands
##
def initializeExperiment():
    global NUM_RACKS, HOSTS_PER_RACK

    print '--- starting experiment...'
    print '--- clearing local arp...'
    call([os.path.expanduser('~/sdrt/cloudlab/clear_arp.sh')])
    print '--- done...'

    print '--- parsing host handles...'
    f = open(NODES_FILE).read().split('\n')[:-1]
    for line in f[1:]:
        handle, hostname = [x.strip() for x in line.split('#')]
        PHYSICAL_NODES.append(handle)
        HANDLE_TO_IP[handle] = hostname
    print '--- done...'

    print '--- checking if mininet is running on hosts...'
    f = open(MININET_NODES_FILE).read().split('\n')[:-1]
    NUM_RACKS = int(f[-1].split('#')[0].strip()[-1])
    RACKS.append([])
    for i in xrange(NUM_RACKS):
        RACKS.append([])
    for line in f:
        handle, ip = [x.strip() for x in line.split('#')]
        rack = int(handle[-2])
        RACKS[rack].append(node(handle))
        HANDLE_TO_IP[handle] = ip
    HOSTS_PER_RACK = len(RACKS[1])
    print '--- done...'

    initializeClickControl()

    print '--- setting default click buffer sizes and traffic sources...'
    setQueueSize(100)
    setEstimateTrafficSource('QUEUE')
    print '--- done...'
    print '--- done starting experiment...'
    print
    print

##
## Running click commands
##    
def initializeClickControl():
    global CLICK_SOCKET
    print '--- connecting to click socket...'
    CLICK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    CLICK_SOCKET.connect((TCP_IP, TCP_PORT))
    CLICK_SOCKET.recv(BUFFER_SIZE)
    print '--- done...'

def clickWriteHandler(element, handler, value):
    message = "WRITE %s.%s %s\n" % (element, handler, value)
    print message.strip()
    CLICK_SOCKET.send(message)
    print CLICK_SOCKET.recv(BUFFER_SIZE).strip()

def clickReadHandler(element, handler):
    message = "READ %s.%s\n" % (element, handler)
    print message.strip()
    CLICK_SOCKET.send(message)
    data = CLICK_SOCKET.recv(BUFFER_SIZE).strip()
    print data
    return data

def setQueueSize(size):
    for i in xrange(len(RACKS) - 1):
        for j in xrange(len(RACKS) - 1):
            clickWriteHandler('hybrid_switch/q%d%d' % (i, j), 'capacity', size)

def setEstimateTrafficSource(source):
    clickWriteHandler('traffic_matrix', 'setSource', source)

def setQueueResize(b):
    if b:
        clickWriteHandler('runner', 'setDoResize', 'true')
    else:
        clickWriteHandler('runner', 'setDoResize', 'false')

##
## Rack level helper functions
##
def rackToRackIperf3(source, dest, fn):
    servers = RACKS[dest]
    for i, host in enumerate(RACKS[source]):
        out_fn = fn + '-%s-%s.txt' % (host.hostname, 'iperf3')
        runOnNode(host.hostname,
                  IPERF3_CLIENT % (host.hostname[1:], servers[i].hostname),
                  fn=out_fn, preload=False)

def rackToRackPing(source, dest, fn):
    servers = RACKS[dest]
    for i, host in enumerate(RACKS[source]):
        out_fn = fn + '-%s-%s.txt' % (host.hostname, 'ping')
        runOnNode(host.hostname, PING % (servers[i].hostname),
                  fn=out_fn, preload=False)




##
## Running shell commands
##
class job:
    def __init__(self, type, server, fn, time, result):
        self.type = type
        self.server = server
        self.fn = fn
        self.time = time
        self.result = result

class node:
    def __init__(self, hostname, skip=False):
        self.hostname = hostname
        self.work = []
        # should probably loop until i connect
        if not skip:
            self.rpc_conn = rpyc.connect(hostname, RPYC_PORT, 
                                         config=rpyc.core.protocol.DEFAULT_CONFIG)
            self.iperf_async = rpyc.async(self.rpc_conn.root.iperf3)
            self.ping_async = rpyc.async(self.rpc_conn.root.ping)

    def iperf3(self, server, fn, time=1):
        if server.__class__ == node:
            server = server.hostname
        r = self.iperf_async(server, time)
        self.work.append(job('iperf3', server, fn, time, r))

    def ping(self, server, fn, time=1):
        if server.__class__ == node:
            server = server.hostname
        r = self.ping_async(server, time)
        self.work.append(job('ping', server, fn, time, r))

    def get_dones(self):
        dones, not_dones = [], []
        for x in self.work:
            if x.result.ready:
                dones.append(x)
            else:
                not_dones.append(x)
        self.work = not_dones
        return dones

    def save_done(self, done):
        rc, sout, serr = done.result.value
        if rc == 0:
            print '%s: %s %s done' % (self.hostname, done.type, done.server)
            print 'fn = %s' % (done.fn)
            open(done.fn, 'w').write(sout)
        else:
            print '%s: error in %s %s %s' % (self.hostname, done.type, 
                                             done.server, done.time)
            print 'fn = %s' % (done.fn)
            sys.stdout.write(sout)
            sys.stdout.write(serr)

def waitWork(host):
    print 'waiting on %s (%s jobs)' % (host.hostname, len(host.work))
    while host.work:
        ds = host.get_dones()
        if ds:
            for d in ds:
                host.save_done(d)

def waitOnWork():
    hosts = [host for rack in RACKS for host in rack]    
    map(waitWork, hosts)

def sshRun(hostname, cmd, printOutput=True):
    out = ""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, timeout=1)
    sesh = client.get_transport().open_session()
    sesh.set_combine_stderr(True)
    sesh.get_pty()

    print cmd
    sesh.exec_command(cmd)

    while True:
        rs, _, _ = select.select([sesh], [], [], 0.0)
        if len(rs) > 0:
            new = sesh.recv(1024)
            out += new
            if printOutput:
                sys.stdout.write(new)
                sys.stdout.flush()
        if sesh.exit_status_ready():
            break
    rc = sesh.recv_exit_status()

    client.close()

    if rc != 0:
        raise Exception('bad RC (%s) from %s cmd: %s\n output: %s' %
                        (rc, hostname, cmd, out))
    return out, rc


##
## Threading
##
def threadRun(hostname, handle, cmd, current, total, fn, po):
    try:
        out = sshRun(hostname, cmd, printOutput=po)[0]
    except Exception, e:
        print e
        out = str(e)
    THREADLOCK.acquire()
    THREADS.remove(hostname)
    if total:
        out = ('(%s/%s) %s:\n' % (current, total, handle)) + out
        if po:
            print '(%s/%s) %s: done\n' % (current, total, handle)
    THREADLOCK.release()
    if fn:
        open(fn, 'w').write(out)

def runOnNode(handle, cmd, current=0, total=0, preload=True, printOutput=True, fn=None):
    try:
        hostname = handle.strip()
        print hostname, cmd, fn
        while len(THREADS) >= MAX_CONCURRENT:
            time.sleep(1)
        THREADLOCK.acquire()
        if preload:
            cmd = 'LD_PRELOAD=%s %s' % (ADU_PRELOAD, cmd)
        threading.Thread(target=threadRun,
                         args=(hostname, handle, cmd, current, total, 
                               fn, printOutput)).start()
        THREADS.append(hostname)
        THREADLOCK.release()
    except Exception, e:
        print e

def waitOnNodes():
    while THREADS:
        time.sleep(1)
