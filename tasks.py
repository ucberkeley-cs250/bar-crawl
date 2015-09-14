
from celery import Celery
from paths import *
from fabric.api import *
from fabric.tasks import execute

app = Celery('tasks', backend='rpc://', broker='redis://boxboro.millennium.berkeley.edu:6379')

sample = "./emulator-Top-DefaultCPPConfig +dramsim +max-cycles=100000000 +verbose +loadmem=../riscv-tests/isa/{}.hex none 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > ../../{}.out && [ $PIPESTATUS -eq 0 ]"

#app.conf.CELERY_ACKS_LATE=True
#app.conf.CELERYD_PREFETCH_MULTIPLIER=10


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



transient_path = '/scratch/sagark/celery-transient/distribute/vcstest/vsim'

def test2(test_to_run):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    #with lcd(distribute_rocket_chip_loc + '/distribute/vcstest/vsim'), shell_env(RISCV=env_RISCV, PATH=env_PATH, LD_LIBRARY_PATH=env_LD_LIBRARY), settings(warn_only=True):
    with lcd(transient_path), shell_env(RISCV=env_RISCV, PATH=env_PATH, LD_LIBRARY_PATH=env_LD_LIBRARY), settings(warn_only=True):
        res = local(samplevcs.format(test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        return "PASS"

@app.task(bind=True)
def vcstest(self, testname):
    rval = execute(test2, testname).values()
    return rval


