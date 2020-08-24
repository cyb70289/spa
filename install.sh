#!/bin/bash
apt install linux-tools-`uname -r` -y
apt install linux-cloud-tools-`uname -r` -y
apt-get install python3-pip -y
#apt-get install python3-pandas -y
apt-get install python3-sh -y
#echo "deb [trusted=yes] https://repo.iovisor.org/apt/bionic bionic-nightly main" | sudo tee /etc/apt/sources.list.d/iovisor.list
#apt-get update
#apt install bcc-tools -y
#apt install python3-bcc -y
##echo "deb http://ddebs.ubuntu.com $(lsb_release -cs) main restricted universe multiverse deb http://ddebs.ubuntu.com $(lsb_release -cs)-updates main restricted universe multiverse  deb http://ddebs.ubuntu.com $(lsb_release -cs)-proposed main restricted universe multiverse" | \tee -a /etc/apt/sources.list.d/ddebs.list
#apt-get update
python3 start.py
git clone https://github.com/brendangregg/FlameGraph.git /opt/FlameGraph

