bar-crawl: Berkeley Architecture Research, Cluster for Running Asic WorkLoads
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

1) bar-crawl starts in your local working copy (/scratch/USERNAME/hwacha-celery), runs jackhammer there to generate a scala file containing your designs, and collects version information (commit hashes) about components of your local install, which it will mimic on worker nodes.

2) bar-crawl will create the following directory structure at your shared output location: 
``` 
output_location/
  2015-12-29-18-56-54-bad3s929/ -- directory names are YYYY-MM-DD-H-M-S-commit_hash
    ConfigName.scala -- generated by jackhammer in the previous step (contains AwesomeDesign0, AwesomeDesign1, etc.)
    AwesomeDesign0/
    AwesomeDesign1/
    AwesomeDesign2/
      emulator/
      vsim/
      vcs-sim-rtl/
      dc-syn/
  2015-12-30-18-56-54-a7d8s9a9/
  riscv-tests/
  ...
``` 
Additionally, bar-crawl will build and install riscv-tests into the shared output location.

3) Currently, bar-crawl reads from the included testnames file to determine which tests should be run. In the future, this will be read directly from the scala source.

4) bar-crawl will then run the compile_and_copy task, which runs through various parts of the build and dispatches tests to workers at individual test granularity as the build progresses. Builds can be monitored through the web interface on the master node (master:8080).

How to use:
-----------------------

1. Choose a "master" node and login. On that node, create a directory:

```
/scratch/YOUR_USERNAME/hwacha-celery
```

Inside it, clone rocket-chip. This will be your working directory. Celery will take the latest commit in this repo and use it to run your distributed tests. For now, Celery pulls from GitHub, so you'll need to make sure that your commit is pushed publicly.

2. Next, you need to start workers on the cluster. Eventually, the workers will be left running. For now, they need to be manually started since they need to be restarted anyway whenever changes are made to bar-crawl. To start the workers:
  [Inside bar-crawl]
  ./run-fabric.sh



Prereqs (TODO):
-----------------------
- TODO: Install celery, fabric or just add mine to PYTHONPATH
- Use ssh forwarding
