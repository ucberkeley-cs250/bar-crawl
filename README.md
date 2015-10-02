bar-crawl: Berkeley Architecture Research - Cluster for Running Asic WorkLoads
==============================================================================

bar-crawl is a distributed build/design space exploration tool for rocket-chip. It uses [jackhammer](http://github.com/ucb-bar/jackhammer) to generate designs from a set of constraints and uses the [Celery Framework](http://www.celeryproject.org/) to distribute jobs across an arbitrary number of machines.

Features:
-----------------------

* Job tracking through a web interface (with [Celery Flower](https://github.com/mher/flower))
* Fine-grained management of tests, since a task is generated per test per test platform per design
* A "watch" script to let you access output from compile jobs on worker nodes, without writing all output to a file.
* Easily scale-up/down machines in your cluster, while jobs are running
* WIP: Lets users share installations of riscv-tools and riscv-tests, but ensures that consistent versions are used
* TODO: Generate designs based on feedback from earlier jobs
* TODO: Store important features from results into DB for easy analysis

Workflow:
-----------------------

1) bar-crawl starts in your local working copy (/scratch/USERNAME/hwacha-celery), runs jackhammer there to generate a scala file containing your designs, collects version information (commit hashes) about components of your local install, and collects patches for any changes in your working copy, which it will mimic on worker nodes.

2) bar-crawl will create the following directory structure at your shared output location: 
``` 
output_location/
  2015-12-29-18-56-54-bad3s929/ -- directory names are YYYY-MM-DD-H-M-S-commit_hash
    ConfigName.scala -- generated by jackhammer in the previous step (contains AwesomeDesign0, AwesomeDesign1, etc.)
    ConfigName0/
    ConfigName1/
    ConfigName2/
      emulator/
      vsim/
      vcs-sim-rtl/
      dc-syn/
    patches/
      rocket-chip.patch -- contains any local changes you have to the rocket-chip repo
      submodules.patch -- contains any local changes you have to submodules (recursive)
  2015-12-30-18-56-54-a7d8s9a9/
  riscv-tests/
  ...
``` 
Additionally, bar-crawl will build and install riscv-tests into the shared output location.

3) Currently, bar-crawl reads from the included testnames file to determine which tests should be run. In the future, this will be read directly from the scala source.

4) bar-crawl will then run the compile_and_copy task, which runs through various parts of the build and dispatches tests to workers at individual test granularity as the build progresses. Builds and test status can be monitored through the web interface on the master node (master:8080). 

5) You can also monitor the compile tasks using the watch script. Run python watch.py and follow the prompts.

Setup:
-----------------------

Add the following to your `.bashrc` (with my username for now) to get `celery`, `flower`, and `redis-server` on your `PATH`/`PYTHONPATH`:

```
export PYTHONPATH=/nscratch/sagark/py_inst/lib/python2.7/site-packages:/nscratch/sagark/py_inst:$PYTHONPATH
export PATH=/nscratch/sagark/bin/bin:/nscratch/sagark/bin:/nscratch/sagark/py_inst/bin:~/bin:$PATH
```

How to use:
-----------------------

0) Choose a master node and login

1) Clone bar-crawl into `/nscratch/YOUR_USERNAME/bar-crawl`

(The rest of this assumes the workers are already running. See below for instructions
for starting a cluster)

2) Set the following variables in `userconfig.py`:

```
username # your username
master_rocket_chip_dir # your rocket-chip working directory
rocket_chip_location # github repo for rocket chip
tests # comment out tests you don't want to run

TODO: add info about setting up email
```

bar-crawl will take the latest commit in master_rocket_chip_dir, generate a set of patches against that commit for any uncommitted changes, and use those to run your distributed tests. bar-crawl pulls from GitHub, so you'll need to make sure that the latest commit on your working copy is pushed to GitHub (but you can also have local changes, which will be mirrored on the workers).

3) If you want to view the web-ui, run the access-web.sh script on your 
machine, then open localhost:8080 in your browser

4) Start the job using

```
python run-job.py
```


Starting a Cluster:
----------------------------

TODO

Prereqs (TODO):
-----------------------
- TODO: Install celery, fabric or just add mine to PYTHONPATH
- Use ssh forwarding
