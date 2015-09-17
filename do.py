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
from tasks import cpptest, vcstest

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

########## Move to tasks.py
def compile_and_copy(design_name):
    design_dir = '/scratch/sagark/celery-temp/' + design_name
    local('mkdir -p ' + design_dir)
    with lcd(design_dir):
        local('git clone ' + repo_location)
    rc_dir = design_dir + '/rocket-chip'
    with lcd(rc_dir):
        local('git submodule update --init')
        # copy designs scala file
        configs_dir = 'src/main/scala/config'
        local('mkdir -p ' + configs_dir)
        local('cp ' + distribute_rocket_chip_loc + '/' + CONF + '.scala ' + configs_dir + '/')

    shell_env_args_conf = copy(shell_env_args)
    shell_env_args_conf['CONFIG'] = design_name
    cpp_emu_name = 'emulator-' + MODEL + '-' + design_name
    vsim_emu_name = 'simv-' + MODEL + '-' + design_name
    with lcd(rc_dir + '/emulator'), shell_env(**shell_env_args_conf):
        local('make ' + cpp_emu_name)
        local('cp -r ../emulator ' + distribute_rocket_chip_loc + '/' + design_name + '/emulator/')
    with lcd(rc_dir + '/vsim'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
        local('make ' + vsim_emu_name)
        local('cp -r ../vsim ' + distribute_rocket_chip_loc + '/' + design_name + '/vsim/')


do_jackhammer()
compile_and_copy(designs[0])




########## TODO: when copying vsim, use cp -Lr to follow dramsim symlink

def build_and_copy_cpp_emu():
    with lcd(distribute_rocket_chip_loc):
        ## cleanup any existing distribute directory
        local('rm -rf distribute')
        ## create directories as necessary (separate commands for clarity)
        local('mkdir distribute')
        # should probably add another level of hierarchy: distribute/designname/cpptest
        local('mkdir distribute/cpptest')
    with lcd(master_rocket_chip_dir+"/emulator"), shell_env(**shell_env_args):
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

"""
checkpref = lambda x: any([x.startswith(y) for y in prefixes])
checksuff = lambda x: all([not x.endswith(y) for y in suffixes])
checkmid = lambda x: all([not y in x for y in mid])

run_t = filter(lambda x: checkpref(x) and checksuff(x) and checkmid(x), t)

print run_t
import random
random.shuffle(run_t)

rs = ResultSet([])
for x in run_t:
    rs.add(vcstest.delay(x))

z = rs.get()
print z
print len(z)
"""
