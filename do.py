""" This is the "master" script. Use fabric to coordinate local ops on
the master.

v1: just parallelize running tests. all compiles happen on the master.
Should be able to just wrap these in @task decorators to make them celery 
tasks eventually. (but then need to move these to tasks.py)
"""

from fabric.api import *
from fabric.tasks import execute

from tasks import add

num_pass = 5000
num_fail = 500


# location of your code on scratch on the master node
master_rocket_chip_dir = "/scratch/sagark/rocket-chip"
# risc-v tools installation. should be on nscratch
rvenv = "/nscratch/sagark/celery-workspace/test-rv"
env_RISCV = rvenv
env_PATH = rvenv+"/bin:$PATH"
MODEL='Top'
CONF = 'DefaultCPPConfig'


distribute_rocket_chip_loc = "/nscratch/sagark/celery-workspace/"




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
        local('cp emulator-' + MODEL + '-DefaultCPPConfig ' + distribute_rocket_chip_loc + 'distribute/cpptest/')
    with lcd(master_rocket_chip_dir+"/riscv-tools"):
        local('cp -r riscv-tests /nscratch/sagark/celery-workspace/distribute/cpptest/')



def test():
    sample = "./emulator-Top-DefaultCPPConfig +dramsim +max-cycles=100000000 +verbose +loadmem=output/rv64ui-v-ori.hex none 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > output/rv64ui-v-ori.out && [ $PIPESTATUS -eq 0 ]"


execute(build_and_copy_cpp_emu)




"""
res = []
for x in range(num_pass):
    res.append(add.delay(34))

for x in range(num_fail):
    res.append(add.delay(3))

for x in range(num_pass+num_fail):
    while not res[x].ready():
        pass


for x in range(num_pass+num_fail):
    print(res[x].get())
"""
