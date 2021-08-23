#!/bin/bash
apt update
apt install linux-tools-`uname -r` -y
apt install linux-cloud-tools-`uname -r` -y
apt-get install python3-pip -y
apt-get install python3-sh -y
[ -d "/opt/FlameGraph" ] && echo "/opt/FlameGraph exists" || git clone https://github.com/brendangregg/FlameGraph.git /opt/FlameGraph
python3 lib/start.py
echo "ENABLED=true" > /etc/default/sysstat
systemctl restart sysstat
