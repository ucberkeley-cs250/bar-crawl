
from celery import Celery
from paths import *
from fabric.api import *
from fabric.tasks import execute
from copy import copy

app = Celery('tasks', backend='rpc://', broker='redis://boxboro.millennium.berkeley.edu:6379')

sample = "./emulator-Top-DefaultCPPConfig +dramsim +max-cycles=100000000 +verbose +loadmem=../riscv-tests/isa/{}.hex none 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > ../../{}.out && [ $PIPESTATUS -eq 0 ]"

#app.conf.CELERY_ACKS_LATE=True
#app.conf.CELERYD_PREFETCH_MULTIPLIER=10

@app.task(bind=True)
def compile_and_copy(self, design_name):
    # remove old results for that design if they exist
    design_dir = '/scratch/sagark/celery-temp/' + design_name
    local('rm -rf ' + design_dir)
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
        local('cp -Lr ../emulator ' + distribute_rocket_chip_loc + '/' + design_name + '/emulator/')
    with lcd(rc_dir + '/vsim'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
        local('make ' + vsim_emu_name)
        local('cp -Lr ../vsim ' + distribute_rocket_chip_loc + '/' + design_name + '/vsim/')
    return "PASS"



def test1(test_to_run):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    with lcd(distribute_rocket_chip_loc + '/distribute/cpptest/emulator'), shell_env(RISCV=env_RISCV, PATH=env_PATH, LD_LIBRARY_PATH=env_LD_LIBRARY), settings(warn_only=True):
        res = local(sample.format(test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        return "PASS"

@app.task(bind=True)
def cpptest(self, testname):
    rval = execute(test1, testname).values()
    return rval

samplevcs = "cd . && ./simv-Top-DefaultVLSIConfig -q +ntb_random_seed_automatic +dramsim +verbose +max-cycles=100000000 +loadmem=../../cpptest/riscv-tests/isa/{}.hex 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > ../../{}.out && [ $PIPESTATUS -eq 0 ]"


def test2(test_to_run):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    with lcd(distribute_rocket_chip_loc + '/distribute/vcstest/vsim'), shell_env(RISCV=env_RISCV, PATH=env_PATH, LD_LIBRARY_PATH=env_LD_LIBRARY), settings(warn_only=True):
        res = local(samplevcs.format(test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        return "PASS"

@app.task(bind=True)
def vcstest(self, testname):
    rval = execute(test2, testname).values()
    return rval


