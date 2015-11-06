bar-crawl: Berkeley Architecture Research - Cluster for Running Asic WorkLoads
==============================================================================

bar-crawl is a distributed build/design space exploration tool for rocket-chip. It uses [jackhammer](http://github.com/ucb-bar/jackhammer) to generate designs from a set of constraints and uses the [Celery Framework](http://www.celeryproject.org/) to distribute jobs across an arbitrary number of machines. It is meant to be used in "live" development, while preserving reproducability efficiently (by preserving hashes and patches of the code and tools used to run jobs).


Features:
-----------------------

* Job tracking through a web interface (with [bar-crawl-web](https://github.com/ucb-bar/bar-crawl-web))
* Fine-grained management of tests, since a task is generated per test (e.g. rv64ui-p-add), per test platform (e.g. vsim), per design (e.g. EOS24Config0).
* A "watch" script to let you access output from compile jobs on worker nodes, without writing all output to a file. This lets you easily track "stuck" jobs that are running remotely.
* Easily scale-up/down machines in your cluster, while jobs are running
* Lets users share installations of riscv-tools and riscv-tests, but ensures that consistent versions are used based on hashes in your working copy
* WIP: Store important features from results into a DB for easy analysis. You can currently access a grid of test results/cycle counts for your job and export CSV results at a8.millennium.berkeley.edu:8080/jobs?limit=10000&jobid=JOB_NAME. For example:

![alt-text](https://www.eecs.berkeley.edu/~skarandikar/host/bar-crawl-screenshot.png "Bar Crawl Screenshot")

* TODO: Generate designs based on feedback from earlier jobs
* TODO: Define queues to dispatch tasks to particular machines
* Your feature here. Submit an [issue](http://github.com/ucb-bar/bar-crawl/issues).


Workflow:
-----------------------

These are not instructions for running a job, but an overview to give you an idea of what bar-crawl does, see the next section for detailed instructions.

1) bar-crawl starts in your local working copy (e.g. /scratch/USERNAME/rocket-chip), runs jackhammer there to generate a scala file containing your designs, collects version information (commit hashes) about components of your local install, and collects patches for any changes in your working copy, which it will mimic on worker nodes.

2) bar-crawl will create the following directory structure at your shared output location (usually `/nscratch/bar-crawl/PROJECT`): 
``` 
/nscratch/bar-crawl/PROJECT/
  2015-12-29-18-56-54-bad3s929/ -- directory names are YYYY-MM-DD-H-M-S-commit_hash
    ConfigName.scala -- generated by jackhammer in the previous step (contains ConfigName0, ConfigName1, etc.)
    ConfigName0/
    ConfigName1/
    ConfigName2/
      emulator/
      vsim/
      vcs-sim-rtl/
      dc-syn/
      vcs-sim-gl-syn/
      icc-par/
    patches/
      rocket-chip.patch -- contains any local changes you have to the rocket-chip repo
      submodules.patch -- contains any local changes you have to submodules (recursive)
  2015-12-30-18-56-54-a7d8s9a9/
  ...
``` 
Additionally, bar-crawl will build and install the correct version of riscv-tests into `/nscratch/bar-crawl/tests-installs`, if it doesn't already exist.

3) bar-crawl will then run the compile_and_copy task, which runs through various parts of the build and dispatches tests to workers at individual test granularity as the build progresses. Builds and test status can be monitored through the web interface on the master node (master:8080). 

4) You can also monitor the compile tasks using the watch script. Run python watch.py and follow the prompts.

Setup:
-----------------------

**Note**: While everything described in this README should work, bar-crawl is still in "beta". Please talk to me (Sagar) if you're interested in using it.

1) Add the following to your `.bashrc` to get `celery` on your `PATH`/`PYTHONPATH`. This will also give you access to `flower` and `redis-server`, but you probably won't need these unless you're running your own workers:

```
export PYTHONPATH=/nscratch/sagark/py_inst/lib/python2.7/site-packages:/nscratch/sagark/py_inst:$PYTHONPATH
export PATH=/nscratch/sagark/bin/bin:/nscratch/sagark/bin:/nscratch/sagark/py_inst/bin:~/bin:$PATH
```

2) Next, make sure that you have the correct version of riscv-tools installed in `/nscratch/bar-crawl/tools-installs`. Inside this directory, installs of riscv-tools are named after the latest commit in the repo from which they were installed. If you need to install a new version, make a directory named after the hash, set `$RISCV` to that directory, and then install the tools. When you run a job, bar-crawl will check the name of this directory against the commit hash of riscv-tools inside your rocket-chip working directory and exit if there is a mismatch.

How to Use bar-crawl:
-----------------------

1) Get a copy of bar-crawl from this repo. You'll want this to be accessible from the machine on which your working copy of rocket-chip is located. You'll need to add the [new-rocketchip branch of jackhammer](https://github.com/ucb-bar/jackhammer/tree/new-rocketchip) as a submodule.

(The rest of this assumes the workers are already running. See below for instructions
for starting a cluster)

2) Set the following variables in `default.conf` (or make your own `.conf` file using `default.conf` as a template):

* `username` - your username
* `master_rocket_chip_dir` - your rocket-chip working directory
* `rvenv` - path to your riscv-tools installation. The directory name should be a commit id.
* `MODEL` - from rocket-chip (currently limited to "Top" due to [this](https://github.com/ucb-bar/jackhammer/commit/fa254a1d60f6a52819ffe9b8c8c9fe211fc3bbae))
* `CONF` - from rocket-chip
* `rocket_chip_url` - github repo for rocket chip
* `tests_url` - github repo for riscv-tests
* `human_tag` - user-specifiable string that will be added to the end of the job name, to let you easily identify the job
* `distribute_rocket_chip_loc` - the directory where your job directories will be created, usually defined per-project
* `enable-email` - Set this to true if you want job completion emails. 
* `email_addr` - An address to send a completion email
* `email_addr2` - A secondary address to send a completion email
* `tests` group - Set items to false if you don't want them to run, e.g. emulator = false

bar-crawl will take the latest commit in master_rocket_chip_dir, generate a set of patches against that commit for any uncommitted changes (except uncommitted submodule bumps, a limitation of git patches), and use those to run your distributed tests. bar-crawl pulls from GitHub, so you'll need to make sure that the latest commit on your working copy is pushed to GitHub (but you can also have local changes, which will be mirrored on the workers). Pulling from GitHub allows you to always test against a "fresh-copy" + patch and means that you don't have to make changes to your working copy (e.g. running make clean) to reduce the amount of data transfer. See the Patching section for a listing of the changes that the bar-crawl patching mechanism can/cannot handle.

3) If you want to view the web-ui, open localhost:8080 on a8 (the current bar-crawl-web host). This page is not publicly visible - a tunnel script is included in `clusterman/ssh-tunnel-a8.sh` or `clusterman/autossh-tunnel-a8.sh`.

4) Start the job using

```
python run-job.py
```

This uses `default.conf`. If you made your own config file that is not named 
`default.conf`, run:

```
python run-job.py YOUR_CONF_FILE
```

Appendices:
------------------------


Patching:
-------------------------
To make it easy to reproduce experiments, versioning of source files used for tests is done by combining a patch of your local changes and a hash from a GitHub repo. The patch mechanism:

* Can distribute changes to tracked files in your working directory and submodules
* Cannot distribute uncommitted/unpushed submodule version bumps (a limitation of git patches, will be eventually fixed manually)
* Cannot distribute untracked files (a TODO)


Starting a Cluster:
----------------------------

TODO

Misc (TODO):
-----------------------
- TODO: Install celery, fabric or just add mine to PYTHONPATH
- Use ssh forwarding
- revoking tests / test timeout
- sudo apt-get install python-dev before installing pip celery
- easy_install --prefix=/nscratch/sagark/py_inst celery[redis]
- easy_install --prefix=/nscratch/sagark/py_inst flower
- manually install redis from source
- "when things go wrong" section
    - check the log for that worker, since celery exceptions like 
    WorkerLostError arise from other exceptions raised in the worker thread

