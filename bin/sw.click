
// For more information, see etalon/bin/gen-switch.py.

define($DEVNAME enp68s0)
define($NUM_RACKS 3)

define($IP1 10.1.100.1, $IP11 10.1.1.1, $IP12 10.1.1.2, $IP13 10.1.1.3, $IP14 10.1.1.4,
       $IP15 10.1.1.5, $IP16 10.1.1.6, $IP17 10.1.1.7, $IP18 10.1.1.8,
       $IP19 10.1.1.9, $IP110 10.1.1.10, $IP111 10.1.1.11, $IP112 10.1.1.12,
       $IP113 10.1.1.13, $IP114 10.1.1.14, $IP115 10.1.1.15, $IP116 10.1.1.16,
       $IP2 10.1.100.2, $IP21 10.1.2.1, $IP22 10.1.2.2, $IP23 10.1.2.3, $IP24 10.1.2.4,
       $IP25 10.1.2.5, $IP26 10.1.2.6, $IP27 10.1.2.7, $IP28 10.1.2.8,
       $IP29 10.1.2.9, $IP210 10.1.2.10, $IP211 10.1.2.11, $IP212 10.1.2.12,
       $IP213 10.1.2.13, $IP214 10.1.2.14, $IP215 10.1.2.15, $IP216 10.1.2.16,
       $IP3 10.1.100.3, $IP31 10.1.3.1, $IP32 10.1.3.2, $IP33 10.1.3.3, $IP34 10.1.3.4,
       $IP35 10.1.3.5, $IP36 10.1.3.6, $IP37 10.1.3.7, $IP38 10.1.3.8,
       $IP39 10.1.3.9, $IP310 10.1.3.10, $IP311 10.1.3.11, $IP312 10.1.3.12,
       $IP313 10.1.3.13, $IP314 10.1.3.14, $IP315 10.1.3.15, $IP316 10.1.3.16)

define ($CIRCUIT_BW_Gbps_TDF 4.0Gbps, $PACKET_BW_Gbps_TDF 0.5Gbps)

define ($PACKET_LATENCY_s_TDF 0.0001)
define ($CIRCUIT_LATENCY_s_TDF 0.0006)
define ($BIG_BUFFER_SIZE 128, $SMALL_BUFFER_SIZE 16)

define ($RECONFIG_DELAY_us 20)
define ($TDF 20)

StaticThreadSched(in 0,
                  traffic_matrix 1,
                  sol 2,
                  runner 3,
                  hybrid_switch/circuit_link1 4,
                  hybrid_switch/circuit_link2 5,
                  hybrid_switch/circuit_link3 6,
                  hybrid_switch/packet_up_link1 7,
                  hybrid_switch/packet_up_link2 7,
                  hybrid_switch/packet_up_link3 7,
                  hybrid_switch/ps/packet_link1 7,
                  hybrid_switch/ps/packet_link2 7,
                  hybrid_switch/ps/packet_link3 7,
)

ControlSocket("TCP", 1239)

traffic_matrix :: EstimateTraffic($NUM_RACKS, SOURCE QUEUE)
sol :: Solstice($NUM_RACKS, $CIRCUIT_BW_Gbps_TDF, $PACKET_BW_Gbps_TDF, $RECONFIG_DELAY_us, $TDF)
runner :: RunSchedule($NUM_RACKS, RESIZE false)

in :: FromDPDKDevice(0, MTU 9000)
out :: ToDPDKDevice(0)

arp_c :: Classifier(12/0800, 12/0806 20/0002, 12/0806 20/0001)
arp_q :: ARPQuerier($DEVNAME:ip, $DEVNAME:eth)
arp_r :: ARPResponder($DEVNAME)

icmptdnsrc :: ICMPTDNUpdate(10.3.100.100, bb:bb:bb:cc:cc:cc, 10.3.0.0, aa:aa:aa:00:00:00, 3, NTDN 2, NRACK 3, NHOST 16, TEST false)

elementclass in_classify {
  input[0] -> IPClassifier(
    src host $IP1 or src host $IP11 or src host $IP12 or src host $IP13 or
    src host $IP14 or src host $IP15 or src host $IP16 or src host $IP17 or src host $IP18 or src host $IP19 or src host $IP110 or src host $IP111 or src host $IP112 or src host $IP113 or src host $IP114 or src host $IP115 or src host $IP116,
    src host $IP2 or src host $IP21 or src host $IP22 or src host $IP23 or
    src host $IP24 or src host $IP25 or src host $IP26 or src host $IP27 or src host $IP28 or src host $IP29 or src host $IP210 or src host $IP211 or src host $IP212 or src host $IP213 or src host $IP214 or src host $IP215 or src host $IP216,
    src host $IP3 or src host $IP31 or src host $IP32 or src host $IP33 or
    src host $IP34 or src host $IP35 or src host $IP36 or src host $IP37 or src host $IP38 or src host $IP39 or src host $IP310 or src host $IP311 or src host $IP312 or src host $IP313 or src host $IP314 or src host $IP315 or src host $IP316
  )
  => [0, 1, 2]output
}

elementclass out_classify {
  input[0] -> IPClassifier(
    dst host $IP1 or dst host $IP11 or dst host $IP12 or dst host $IP13 or
    dst host $IP14 or dst host $IP15 or dst host $IP16 or dst host $IP17 or dst host $IP18 or dst host $IP19 or dst host $IP110 or dst host $IP111 or dst host $IP112 or dst host $IP113 or dst host $IP114 or dst host $IP115 or dst host $IP116,
    dst host $IP2 or dst host $IP21 or dst host $IP22 or dst host $IP23 or
    dst host $IP24 or dst host $IP25 or dst host $IP26 or dst host $IP27 or dst host $IP28 or dst host $IP29 or dst host $IP210 or dst host $IP211 or dst host $IP212 or dst host $IP213 or dst host $IP214 or dst host $IP215 or dst host $IP216,
    dst host $IP3 or dst host $IP31 or dst host $IP32 or dst host $IP33 or
    dst host $IP34 or dst host $IP35 or dst host $IP36 or dst host $IP37 or dst host $IP38 or dst host $IP39 or dst host $IP310 or dst host $IP311 or dst host $IP312 or dst host $IP313 or dst host $IP314 or dst host $IP315 or dst host $IP316
  )
  => [0, 1, 2]output
}

elementclass packet_link {
  input[0, 1, 2]
    => RoundRobinSched
    -> lu :: LinkUnqueue($PACKET_LATENCY_s_TDF, $PACKET_BW_Gbps_TDF)
    -> output
}

elementclass circuit_link {
  input[0, 1, 2]
    => ps :: SimplePullSwitch(-1)
    -> lu :: LinkUnqueue($CIRCUIT_LATENCY_s_TDF, $CIRCUIT_BW_Gbps_TDF)
    -> StoreData(1, 1) -> SetIPChecksum
    -> output
}

elementclass packet_switch {
  c1, c2, c3 :: out_classify

  q11, q12, q13,
  q21, q22, q23,
  q31, q32, q33
 :: Queue(CAPACITY 3)

  packet_link1, packet_link2, packet_link3 :: packet_link

  input[0] -> c1 => q11, q12, q13
  input[1] -> c2 => q21, q22, q23
  input[2] -> c3 => q31, q32, q33

  q11, q21, q31 => packet_link1 -> [0]output
  q12, q22, q32 => packet_link2 -> [1]output
  q13, q23, q33 => packet_link3 -> [2]output

  q11[1], q12[1], q13[1] -> [3]output
  q21[1], q22[1], q23[1] -> [4]output
  q31[1], q32[1], q33[1] -> [5]output
}

hybrid_switch :: {
  c1, c2, c3 :: out_classify

  q11, q12, q13,
  q21, q22, q23,
  q31, q32, q33
 :: {
      input[0] -> q :: LockQueue(CAPACITY $SMALL_BUFFER_SIZE)
      input[1] -> lq :: Queue(CAPACITY 5)
      lq, q => PrioSched -> output
 }

  circuit_link1, circuit_link2, circuit_link3 :: circuit_link

  packet_up_link1, packet_up_link2, packet_up_link3 :: packet_link

  ps :: packet_switch

  input[0] -> Paint(1, 20) -> c1 => q11, q12, q13
  input[1] -> Paint(2, 20) -> c2 => q21, q22, q23
  input[2] -> Paint(3, 20) -> c3 => q31, q32, q33

  q11, q21, q31 => circuit_link1 -> Paint(1, 21) -> [0]output
  q12, q22, q32 => circuit_link2 -> Paint(2, 21) -> [1]output
  q13, q23, q33 => circuit_link3 -> Paint(3, 21) -> [2]output

  q11 -> pps11 :: SimplePullSwitch(0)
  q12 -> pps12 :: SimplePullSwitch(0)
  q13 -> pps13 :: SimplePullSwitch(0)
  q21 -> pps21 :: SimplePullSwitch(0)
  q22 -> pps22 :: SimplePullSwitch(0)
  q23 -> pps23 :: SimplePullSwitch(0)
  q31 -> pps31 :: SimplePullSwitch(0)
  q32 -> pps32 :: SimplePullSwitch(0)
  q33 -> pps33 :: SimplePullSwitch(0)
  pps11, pps12, pps13 => packet_up_link1 -> [0]ps[0] -> Paint(1, 21) -> [0]output
  pps21, pps22, pps23 => packet_up_link2 -> [1]ps[1] -> Paint(2, 21) -> [1]output
  pps31, pps32, pps33 => packet_up_link3 -> [2]ps[2] -> Paint(3, 21) -> [2]output

  ps[3] -> out_classify => [1]q11, [1]q12, [1]q13
  ps[4] -> out_classify => [1]q21, [1]q22, [1]q23
  ps[5] -> out_classify => [1]q31, [1]q32, [1]q33
}

in -> arp_c
   -> MarkIPHeader(14)
   -> StripToNetworkHeader 
   -> GetIPAddress(IP dst)
   -> pc :: IPClassifier(dst host $DEVNAME:ip icmp echo, -)[1] 
   -> divert_acks :: Switch(0)
   -> st :: SetTimestamp(FIRST true) 
   -> hsl :: HSLog($NUM_RACKS)
   -> in_classify[0, 1, 2]
   => hybrid_switch[0, 1, 2]
   -> ecem :: ECEMark($NUM_RACKS)
   -> ecn :: MarkIPCE(FORCE true)
   -> arp_q 
   -> out

divert_acks[1] -> acks :: IPClassifier(tcp ack and len < 100, -)[1] -> st
acks -> arp_q

arp_c[1] -> [1]arp_q
arp_c[2] -> arp_r -> out

pc -> ICMPPingResponder -> arp_q

icmptdnsrc -> Queue(CAPACITY 20) -> out
