#!/bin/python3
from sh import Command
import subprocess
import re
import json
import os

out =  subprocess.Popen(["../libpfm4/examples/showevtinfo"],  stdout=subprocess.PIPE);
output = out.communicate()[0];
filename = "log_file"
mapped_values = {"Name": "EventName", "Desc": "Description", "Code": "Code"}
with open(filename, "w+") as f:
    f.write(output.decode())
counters = []
name_re = "(Code|Desc|Name)\s*:\s*([\w -]+)";
codes_re = "Codes\s*:\s*([\w ]+)";
tmp = None
for line in  open(filename, "r"):
    match = re.match(name_re, line);
    if match:
        if match.group(1) == "Name":
            try:
                out =  subprocess.Popen(["../libpfm4/examples/check_events", match.group(2)],  stdout=subprocess.PIPE, stderr=subprocess.PIPE);
            except Exception as e:
                print("war")
            finally:
                output, err = out.communicate();
                output = output.decode()
            if tmp != None:
               counters.append(tmp)
            tmp = {}
            match_code = re.search(codes_re, output)
            if match_code:
                tmp["Perf-Code"] = 'r' + match_code.group(1).strip()[2:]
            else:
                tmp["Perf-Code"] = 'NA'


        tmp[mapped_values[match.group(1).strip()]] = match.group(2).strip()        

os.remove(filename)

with open("pmu_events.json", "w+") as pmu_file:
    json.dump(counters, pmu_file, indent=2)

