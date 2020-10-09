The application automates capturing of workload performance metrics through
perf and ebpf tools. 

Each supported tool has a set of options that can be provided on the command line
and can be checked out by typing:

 python3 main.py <tool> --help.

Alternatively, there is a virtual interface (recommended) that can be used to run
your configuration. The virtual interface uses the values in the configuration
files inside run_configurations/ referenced to in the config.yaml file to 
set up the command line parameters for the desired performance tool.

Once the configuration files are set up just run:

python3 virtif.py

The verbosity can be setup in the configuration files. If set to High the logs are displayed.
Else the logs are written in profiler.log. 

The output files are placed in ../output/.

Once a basic configuration file is written for the test, the individual parameters for the 
configuration files can be changed on runtime by adding the argument to the virtif.py command line.

For example if the type of my test in the configuration file is set to "All" and I want to change it
to "Analysis" I just need to type python3 virtif.py type=Analysis. This way we do not need
to change the configuration file for each run.


NOTE: All the parameters of the top level config.yaml file cannot be changed during runtime.

Constraints as of this release: There are sample configuration files provided for all the different 
tools supported so not much needs to be changed. Changing the command line in config.yaml and the 
pmu_file path should make most of the experiments work. The default values for all the tests
are mentioned in defaults.yaml. Individual config files updates the parameters in the defau;t file.


Tips:

Remove PMU_logs/ for a fresh perf stat monitoring
Remove PMU_rec_logs/ for a fresh perf record sampling
Remove Ebpf_logs/ for a fresh ebpf trace
