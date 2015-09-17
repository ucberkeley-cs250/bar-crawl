""" This is the "master" script. Use fabric to coordinate local ops on
the master.

v1: just parallelize running tests. all compiles happen on the master.
Should be able to just wrap these in @task decorators to make them celery 
tasks eventually. (but then need to move these to tasks.py)
"""

from celery.result import ResultSet

from fabric.api import *
from fabric.tasks import execute
from copy import copy
from tasks import cpptest, vcstest, compile_and_copy

# filenames
from paths import *
import os

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
        local('git clone git@github.com:ucb-bar/riscv-tests')
        local('cd riscv-tests && git submodule update --init')
        local('cd riscv-tests/isa && make -j32')

do_jackhammer()
build_riscv_tests()
#compile_and_copy(designs[0])



#### TODO should get the list of tests from Testing.scala
t = os.listdir(distribute_rocket_chip_loc + '/riscv-tests/isa/') 

prefixes = ['rv64ui-v-', 'rv64ua-v-', 'rv64ui-p-', 'rv64ui-pt-', 'rv64um-pt-', 'rv64uf-v-', 'rv64uf-p-', 'rv64si-p-', 'rv64um-v-', 'rv64mi-p-', 'rv64ua-pt-', 'rv64uf-pt-']
suffixes = ['.hex', '.dump']
mid = ['-vec-']
mid += ["rv64ui-p-amoadd_d",
"rv64ui-p-amoadd_w",
"rv64ui-p-amoand_d",
"rv64ui-p-amoand_w",
"rv64ui-p-amomax_d",
"rv64ui-p-amomaxu_d",
"rv64ui-p-amomaxu_w",
"rv64ui-p-amomax_w",
"rv64ui-p-amomin_d",
"rv64ui-p-amominu_d",
"rv64ui-p-amominu_w",
"rv64ui-p-amomin_w",
"rv64ui-p-amoor_d",
"rv64ui-p-amoor_w",
"rv64ui-p-amoswap_d",
"rv64ui-p-amoswap_w",
"rv64ui-p-amoxor_d",
"rv64ui-p-amoxor_w",
"rv64ui-p-div",
"rv64ui-p-divu",
"rv64ui-p-divuw",
"rv64ui-p-divw",
"rv64ui-p-example",
"rv64ui-p-mulh",
"rv64ui-p-mulhsu",
"rv64ui-p-mulhu",
"rv64ui-p-mul",
"rv64ui-p-mulw",
"rv64ui-p-rem",
"rv64ui-p-remu",
"rv64ui-p-remuw",
"rv64ui-p-remw",
"rv64ui-pt-example",
"rv64ui-v-example"]

checkpref = lambda x: any([x.startswith(y) for y in prefixes])
checksuff = lambda x: all([not x.endswith(y) for y in suffixes])
checkmid = lambda x: all([not y in x for y in mid])

run_t = filter(lambda x: checkpref(x) and checksuff(x) and checkmid(x), t)

print run_t

compiles = ResultSet([])
for x in designs:
    compiles.add(compile_and_copy.delay(x))

y = compiles.get()

"""
rs = ResultSet([])
for x in run_t:
    rs.add(vcstest.delay(x))

z = rs.get()
print z
print len(z)
"""
