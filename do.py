""" This is the "master" script. Use fabric to coordinate local ops on
the master.

v1: just parallelize running tests. all compiles happen on the master.
Should be able to just wrap these in @task decorators to make them celery 
tasks eventually. (but then need to move these to tasks.py)
"""

from celery.result import ResultSet

from fabric.api import *
from fabric.tasks import execute

from tasks import cpptest, vcstest

# filenames
from paths import *
import os


########## TODO: when copying vsim, use cp -Lr to follow dramsim symlink

def build_and_copy_cpp_emu():
    with lcd(distribute_rocket_chip_loc):
        ## cleanup any existing distribute directory
        local('rm -rf distribute')
        ## create directories as necessary (separate commands for clarity)
        local('mkdir distribute')
        # should probably add another level of hierarchy: distribute/designname/cpptest
        local('mkdir distribute/cpptest')
    with lcd(master_rocket_chip_dir+"/emulator"), shell_env(RISCV=env_RISCV, PATH=env_PATH):
        local('make clean')
        local('make emulator-' + MODEL + '-DefaultCPPConfig')
        # copy c++ emulator binary to nscratch
        local('cp -r ../emulator ' + distribute_rocket_chip_loc + 'distribute/cpptest/')
    with lcd(master_rocket_chip_dir+"/riscv-tools"):
        local('cp -r riscv-tests /nscratch/sagark/celery-workspace/distribute/cpptest/')

    with lcd(distribute_rocket_chip_loc + "distribute/cpptest/riscv-tests/isa/"), shell_env(RISCV=env_RISCV, PATH=env_PATH, LD_LIBRARY_PATH=env_LD_LIBRARY):
        # build the tests on master node
        # faster than building then copying...
        # and i'm guessing faster than a bunch of distributed writes from 
        # workers
        local('make -j32')




t = os.listdir(distribute_rocket_chip_loc + 'distribute/cpptest/riscv-tests/isa/') 

prefixes = ['rv64ui-v-', 'rv64ua-v-', 'rv64ui-p-', 'rv64ui-pt-', 'rv64um-pt-', 'rv64uf-v-', 'rv64uf-p-', 'rv64si-p-', 'rv64um-v-', 'rv64mi-p-', 'rv64ua-pt-', 'rv64uf-pt-']
suffixes = ['.hex', '.dump']
mid = ['-vec-']

checkpref = lambda x: any([x.startswith(y) for y in prefixes])
checksuff = lambda x: all([not x.endswith(y) for y in suffixes])
checkmid = lambda x: all([not y in x for y in mid])

run_t = filter(lambda x: checkpref(x) and checksuff(x) and checkmid(x), t)

print run_t
rs = ResultSet([])
for x in run_t:
    rs.add(vcstest.delay(x))

z = rs.get()
print z
print len(z)

#vcstest.delay("rv64ui-pt-mulhu")
