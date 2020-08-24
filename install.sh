#!/bin/bash
apt install linux-tools-`uname -r` -y
apt install linux-cloud-tools-`uname -r` -y
apt-get install python3-pip -y
apt-get install python3-sh -y
python3 lib/start.py
git clone https://github.com/brendangregg/FlameGraph.git /opt/FlameGraph

