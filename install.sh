#!/bin/bash
apt update
apt install linux-tools-`uname -r` -y
apt install linux-cloud-tools-`uname -r` -y
apt-get install python3-pip -y
apt-get install python3-sh -y
[ -d "/opt/FlameGraph" ] && echo "/opt/FlameGraph exists" || git clone https://github.com/brendangregg/FlameGraph.git /opt/FlameGraph
wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add -
apt-add-repository "deb http://apt.llvm.org/focal/ llvm-toolchain-focal-13 main"
apt-get update
python3 lib/start.py
apt install -y sysstat
echo "ENABLED=true" > /etc/default/sysstat
systemctl restart sysstat
perf config stat.big-num=false
