""" This is the "master" script. Use fabric to coordinate local ops on
the master.
"""

from celery.result import ResultSet

from fabric.api import *
from fabric.tasks import execute
from copy import copy
from tasks import cpptest, vcstest, compile_and_copy

# filenames
from paths import *
import os

# hashes to check against to make sure we're using consistent tools
# and to name output directories
hashes = get_hashes()

# populated by do_jackhammer
designs = []

def do_jackhammer():
    with lcd(master_rocket_chip_dir + '/jackhammer'), shell_env(**shell_env_args):
        local('make')
    designs_scala = master_rocket_chip_dir + '/src/main/scala/config/' + CONF + '.scala'

    local('cp ' + designs_scala + ' ' + distribute_rocket_chip_loc)

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
        for y in tests:
            local('mkdir -p ' + distribute_rocket_chip_loc + '/' + x + '/' + y)

def build_riscv_tests():
    with lcd(distribute_rocket_chip_loc), shell_env(**shell_env_args), settings(warn_only=True):
        # build the tests on master node
        # faster than building then copying...
        # and i'm guessing faster than a bunch of distributed writes from 
        # workers
        local('git clone ' + tests_location)
        local('cd esp-tests && git submodule update --init')
        local('cd esp-tests/isa && make -j32')

do_jackhammer()
build_riscv_tests()



#### TODO should get the list of tests from Testing.scala
tfile = open('testnames', 'r')
run_t = map(lambda x: x.strip(), tfile.readlines())
tfile.close()

print run_t

compiles = ResultSet([])
for x in designs:
    compiles.add(compile_and_copy.delay(x, hashes))

y = compiles.get()


rs = ResultSet([])
for y in designs:
    for x in run_t:
        rs.add(vcstest.delay(y, x))

z = rs.get()
print z
print len(z)
