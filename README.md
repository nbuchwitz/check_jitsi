# check_jitsi
Icinga check command for jitsi video conference server

## Setup

### Requirements

This check command depends on **Python 3** and the following modules:
 * enum
 * requests
 * argparse

**Installation on Debian / Ubuntu**
```
apt install python3 python3-requests
```

**Installation on Redhat 7 / CentOS 7**
```
yum install python36 python36-requests
```

**Installation on FreeBSD**
```
pkg install python3 py37-requests
```


### Activate private rest API on jitsi videobridge

Enable rest api in jitsi videobridge by appending `--apis=rest` to the `JVB_OPTS` in `/etc/jitsi/videobridge/config`:

```
[...]
JVB_OPTS="--apis=rest,xmpp"
[...]
```

Edit `/etc/jitsi/videobridge/sip-communicator.properties` and enable statistics:

```
[...]
org.jitsi.videobridge.ENABLE_STATISTICS=true
[...]
```

Restart the `jvb` and `jicofo` service

#### Troubleshooting

If using openjdk and you see lots of errors in your videobridge logs, try to enable `jdk.management/com.sun.management`, by editing `/etc/jitsi/videobridge/config`:

before:
```
JAVA_SYS_PROPS="-Dnet.java.sip.communicator.SC_HOME_DIR_LOCATION=/etc/jitsi -Dnet.java.sip.communicator.SC_HOME_DIR_NAME=videobridge -Dnet.java.sip.communicator.SC_LOG_DIR_LOCATION=/var/log/jitsi -Djava.util.logging.config.file=/etc/jitsi/videobridge/logging.properties"
```

after:
```
JAVA_SYS_PROPS="-Dnet.java.sip.communicator.SC_HOME_DIR_LOCATION=/etc/jitsi -Dnet.java.sip.communicator.SC_HOME_DIR_NAME=videobridge -Dnet.java.sip.communicator.SC_LOG_DIR_LOCATION=/var/log/jitsi -Djava.util.logging.config.file=/etc/jitsi/videobridge/logging.properties --add-opens jdk.management/com.sun.management.internal=ALL-UNNAMED"
```

More more details see here https://github.com/jitsi/jitsi-videobridge/issues/1127#issuecomment-601539870.

## Usage

```
usage: check_jitsi.py [-h] [-H HOSTNAME] [-p PORT] -m
                      {health,participants,conferences,audiochannels,videochannels,videostreams,total_conferences_completed,total_conferences_created,total_conferences_failed,total_partially_failed_conferences,jitter_aggregate,total_no_payload_channels,total_no_transport_channels}
                      [-w THRESHOLD] [-c THRESHOLD] [--all-metrics]
                      [--ignore-metric METRIC]

Check command for JVB via API

optional arguments:
  -h, --help            show this help message and exit
  -H HOSTNAME, --hostname HOSTNAME
                        JVB private api hostname
  -p PORT, --port PORT  JVB private api port
  -m {health,participants,conferences,audiochannels,videochannels,videostreams,total_conferences_completed,total_conferences_created,total_conferences_failed,total_partially_failed_conferences,jitter_aggregate,total_no_payload_channels,total_no_transport_channels}, --mode {health,participants,conferences,audiochannels,videochannels,videostreams,total_conference
s_completed,total_conferences_created,total_conferences_failed,total_partially_failed_conferences,jitter_aggregate,total_no_payload_channels,total_no_transport_channels}
                        Check mode
  -w THRESHOLD, --warning THRESHOLD
                        Warning threshold for check value
  -c THRESHOLD, --critical THRESHOLD
                        Critical threshold for check value
  --all-metrics
  --ignore-metric METRIC
                        Ignore this metric in the performance data
```

## Examples

**Check jitsi health**
```
./check_jitsi.py -m health
OK - Jitsi videobridge is healthy 
```

with all metrics:

```
./check_jitsi.py -m health --all-metrics 
OK - Jitsi videobridge is healthy |packet_rate_download=0 total_tcp_connections=0 total_packets_sent_octo=0 total_loss_degraded_participant_seconds=0 bit_rate_download=0 videostreams=0 jitter_aggregate=0.0 total_channels=8 total_memory=16821 total_packets_received=13694 rtt_aggregate=0.0 packet_rate_upload=0 conferences=0 participants=0 total_loss_limited_participant_seconds=0 largest_conference=0 total_packets_sent=3030 total_data_channel_messages_sent=609 total_bytes_received_octo=0 total_no_transport_channels=0 total_no_payload_channels=4 used_memory=1518 total_conferences_created=2 threads=82 total_colibri_web_socket_messages_received=0 videochannels=0 total_udp_connections=4 loss_rate_upload=0.0 total_packets_received_octo=0 graceful_shutdown=0 total_colibri_web_socket_messages_sent=0 total_bytes_sent_octo=0 total_data_channel_messages_received=633 loss_rate_download=0.0 total_conference_seconds=802 total_bytes_received=9662349 rtp_loss=0.0 total_loss_controlled_participant_seconds=0 total_partially_failed_conferences=2 bit_rate_upload=0 total_conferences_completed=2 total_bytes_sent=99326 total_failed_conferences=0 cpu_usage=0.005 audiochannels=0
```

**Check specific metric**

It's possible to check if a certain metric is within the specified thresholds for warning and critical (full syntax supported):
```
./check_jitsi.py -m total_conferences_failed -w 5 -c 10
OK - 0 total_conferences_failed |total_conferences_failed=0;;5;10

```

## Integration in Icinga2

Example configuration files for Icinga2 are in the folder `icinga/`.
