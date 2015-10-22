""" This is the master script for running bar crawl. Once you've set things up
in userconfig.py, you can run jobs using:
python run-job.py
"""

from celery.result import ResultSet
from fabric.api import *
from fabric.tasks import execute
from copy import copy
from tasks import *
import os
import datetime

from userconfig import UserJobConfig
from crawlutils import *

userjobconfig = UserJobConfig()

workers = app.control.inspect().ping()
if workers == None:
    print(bcolors.FAIL + "There are no workers running. Please start workers." + bcolors.ENDC)
    exit(1)

# check that we're using workers consistent with our version of bar-crawl
h = get_hash(os.getcwd())[:8]
mismatch_found = False
for worker in workers:
    if h not in worker:
        print("Mismatched worker found: " + worker)
        mismatch_found = True

if mismatch_found:
    msg = """bar-crawl cannot run with mismatched workers. This probably means that you 
need to update your local version of bar-crawl."""
    print(bcolors.FAIL + msg + bcolors.ENDC)
    exit(1)


# launchtime
dtstr = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

# hashes to check against to make sure we're using consistent tools
# and to name output directories
hashes = get_hashes(userjobconfig.master_rocket_chip_dir)
userjobconfig.hashes = hashes

# check if the riscv-tools we're supposed to be using matches what's installed:
if hashes['riscv-tools'] != userjobconfig.rvenv_installed_hash:
    print(bcolors.FAIL + "riscv-tools hash mismatch:" + bcolors.ENDC)
    print("Installed: " + userjobconfig.rvenv_installed_hash)
    print("Required:  " + hashes['riscv-tools'])
    exit(1)

jobdirname = dtstr + '-' + hashes['rocket-chip'][:8] + userjobconfig.human_tag
fulljobdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobdirname
local('mkdir -p ' + fulljobdir)

# populated by do_jackhammer
designs = []

def do_jackhammer():
    with lcd(userjobconfig.master_rocket_chip_dir + '/jackhammer'), shell_env(**userjobconfig.shell_env_args):
        local('make')
    designs_scala = userjobconfig.master_rocket_chip_dir + '/src/main/scala/config/' + userjobconfig.CONF + '.scala'

    local('cp ' + designs_scala + ' ' + fulljobdir)

    ## GET/populate list of design names
    a = open(designs_scala, 'r')
    b = a.readlines()
    a.close()

    for x in b:
        linesplit = x.split(' ')
        if linesplit[0] == 'class':
            designs.append(linesplit[1])

    print("Detected Designs:")
    print(designs)
   
    #create a directory in distribute for each design, test
    for x in designs:
        for y in userjobconfig.tests:
            local('mkdir -p ' + fulljobdir + '/' + x + '/' + y)
        # always make the emulator directory
        local('mkdir -p ' + fulljobdir + '/' + x + '/emulator')

    # directory to store patches if there are local changes
    patchdir = fulljobdir + '/patches'
    local('mkdir -p ' + patchdir)
    generate_recursive_patches(userjobconfig.master_rocket_chip_dir, patchdir)

def build_riscv_tests():
    # sanity check that the riscv-tests hash is not the same as the riscv-tools hash
    # (this probably means that you forgot to do git submodule update --init inside riscv-tools)
    if hashes['riscv-tests'] == hashes['riscv-tools']:
        print(bcolors.FAIL + "riscv-tests hash matches riscv-tools hash. Did you forget to init the\nriscv-tests submodule?" + bcolors.ENDC)
        exit(1)
    with lcd('/nscratch/bar-crawl/tests-installs'), shell_env(**userjobconfig.shell_env_args), settings(warn_only=True):
        local('git clone ' + userjobconfig.tests_location + ' ' + hashes['riscv-tests'])
        local('cd ' + hashes['riscv-tests'] + ' && git checkout ' + hashes['riscv-tests'])
        local('cd ' + hashes['riscv-tests'] + ' && git submodule update --init')
        local('cd ' + hashes['riscv-tests'] + '/isa && make -j32')

do_jackhammer()
build_riscv_tests()

compiles = ResultSet([])
for x in designs:
    compiles.add(compile_and_copy.delay(x, hashes, jobdirname, userjobconfig))

print(bcolors.OKBLUE + "Your job has been launched. You can monitor it at a8:8080" + bcolors.ENDC)
print(bcolors.OKGREEN + "Your job id is " + jobdirname + bcolors.ENDC)


# TODO generate job run report
# 1 whether or not new tests/tools were installed
# 2 where to find outputs
# 3 how to use watch script
# 4 jobid
# 5 write it to file so that the watch script can use it

