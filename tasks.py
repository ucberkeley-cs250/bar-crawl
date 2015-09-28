import redis

from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from paths import *
from fabric.api import *
from fabric.tasks import execute
from copy import copy

app = Celery('tasks', backend='rpc://', broker=redis_conf_string)

sample = "./emulator-Top-DefaultCPPConfig +dramsim +max-cycles=100000000 +verbose +loadmem=../esp-tests/isa/{}.hex none 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > ../../{}.out && [ $PIPESTATUS -eq 0 ]"

#app.conf.CELERY_ACKS_LATE=True
#app.conf.CELERYD_PREFETCH_MULTIPLIER=10

@app.task(bind=True)
def compile_and_copy(self, design_name, hashes, jobinfo):
    rl = RedisLogger(design_name)
    design_dir = '/scratch/sagark/celery-temp/' + design_name
    # remove old results for that design if they exist
    rl.local_logged('rm -rf ' + design_dir)
    rl.local_logged('mkdir -p ' + design_dir)
    with lcd(design_dir):
        rl.local_logged('git clone ' + rocket_chip_location)
    rc_dir = design_dir + '/rocket-chip'
    with lcd(rc_dir):
        # checkout the correct hash
        rl.local_logged('git checkout ' + hashes['rocket-chip'])
        rl.local_logged('git submodule update --init')
        # copy designs scala file
        configs_dir = 'src/main/scala/config'
        rl.local_logged('mkdir -p ' + configs_dir)
        rl.local_logged('cp ' + distribute_rocket_chip_loc + '/' + jobinfo + '/' + CONF + '.scala ' + configs_dir + '/')

    with lcd(rc_dir + '/vlsi'):
        rl.local_logged('git submodule update --init --recursive')

    shell_env_args_conf = copy(shell_env_args)
    shell_env_args_conf['CONFIG'] = design_name
    cpp_emu_name = 'emulator-' + MODEL + '-' + design_name
    vsim_emu_name = 'simv-' + MODEL + '-' + design_name
    with lcd(rc_dir + '/emulator'), shell_env(**shell_env_args_conf):
        rl.local_logged('make ' + cpp_emu_name)
        rl.local_logged('cp -Lr ../emulator ' + distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/emulator/')
    with lcd(rc_dir + '/vsim'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
        rl.local_logged('make ' + vsim_emu_name)
        rl.local_logged('cp -Lr ../vsim ' + distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vsim/')
    with lcd(distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name):
        rl.local_logged('cp -r emulator/emulator/dramsim2_ini vsim/vsim/')
    with lcd(rc_dir + '/vlsi/vcs-sim-rtl'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
        rl.local_logged('make ' + vsim_emu_name)
        rl.local_logged('cp -Lr ../vcs-sim-rtl ' + distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-rtl/')
    with lcd(distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name):
        rl.local_logged('cp -r emulator/emulator/dramsim2_ini vsim/vsim/')
        rl.local_logged('cp -r emulator/emulator/dramsim2_ini vcs-sim-rtl/vcs-sim-rtl/')

    # vlsi, dc
    rl2 = RedisLoggerStream(design_name)
    with lcd(rc_dir + '/vlsi/dc-syn'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
        rl2.local_logged('make 2>&1')

    #rl.clear_log() # clear the redis log list
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

samplevcs = "cd . && ./simv-Top-{} -q +ntb_random_seed_automatic +dramsim +verbose +max-cycles=100000000 +loadmem=../../../../esp-tests/isa/{}.hex 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > ../{}.out && [ $PIPESTATUS -eq 0 ]"


def vsim(design_name, test_to_run, jobinfo):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    workdir = distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vsim/vsim'
    with lcd(workdir), shell_env(**shell_env_args), settings(warn_only=True):
        res = local(samplevcs.format(design_name, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        return "PASS"

# 5 min timeout per test
@app.task(bind=True, soft_time_limit=300)
def vsimtest(self, design_name, testname, jobinfo):
    try:
        rval = execute(vsim, design_name, testname, jobinfo).values()
        return rval
    except SoftTimeLimitExceeded:
        return "FAILED RAN OUT OF TIME"

samplevcs_sim_rtl = 'cd . && ./simv-Top-{} -q +ntb_random_seed_automatic +dramsim +verbose +max-cycles=100000000 +loadmem=../../../../esp-tests/isa/{}.hex 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/hwacha-rv/bin/spike-dasm  > ../{}.out && [ $PIPESTATUS -eq 0 ]'

def vcs_sim_rtl(design_name, test_to_run, jobinfo):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    workdir = distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-rtl/vcs-sim-rtl'
    with lcd(workdir), shell_env(**shell_env_args), settings(warn_only=True):
        res = local(samplevcs_sim_rtl.format(design_name, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        return "PASS"

# 5 min timeout per test
@app.task(bind=True, soft_time_limit=300)
def vcs_sim_rtl_test(self, design_name, testname, jobinfo):
    try:
        rval = execute(vcs_sim_rtl, design_name, testname, jobinfo).values()
        return rval
    except SoftTimeLimitExceeded:
        return "FAILED RAN OUT OF TIME"

