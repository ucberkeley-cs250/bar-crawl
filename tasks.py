import redis

from celery import Celery
from celery.result import ResultSet
from celery.exceptions import SoftTimeLimitExceeded
from crawlutils import *
from fabric.api import *
from fabric.tasks import execute
from copy import copy

app = Celery('tasks', backend='rpc://', broker=redis_conf_string)

sample = "./emulator-Top-DefaultCPPConfig +dramsim +max-cycles=100000000 +verbose +loadmem=../esp-tests/isa/{}.hex none 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > ../../{}.out && [ $PIPESTATUS -eq 0 ]"

#app.conf.CELERY_ACKS_LATE=True
#app.conf.CELERYD_PREFETCH_MULTIPLIER=10

@app.task(bind=True)
def compile_and_copy(self, design_name, hashes, jobinfo, userjobconfig):
    rs = ResultSet([])

    rl = RedisLogger(design_name)
    rl2 = RedisLoggerStream(design_name)

    # create scratch space on this node for compiling the design, then clone
    design_dir = '/scratch/' + userjobconfig.username + '/celery-temp/' + design_name
    # remove old results for that design if they exist
    rl.local_logged('rm -rf ' + design_dir)
    rl.local_logged('mkdir -p ' + design_dir)
    with lcd(design_dir):
        rl.local_logged('git clone ' + userjobconfig.rocket_chip_location)
    rc_dir = design_dir + '/rocket-chip'
    with lcd(rc_dir):
        # checkout the correct hash
        rl.local_logged('git checkout ' + hashes['rocket-chip'])
        rl.local_logged('git submodule update --init')
        # copy designs scala file
        configs_dir = 'src/main/scala/config'
        rl.local_logged('mkdir -p ' + configs_dir)
        rl.local_logged('cp ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + userjobconfig.CONF + '.scala ' + configs_dir + '/')
    with lcd(rc_dir + '/vlsi'):
        rl.local_logged('git submodule update --init --recursive')

    # now, apply patches
    apply_recursive_patches(userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/patches', rc_dir)

    # at this point, design_dir/rocket-chip will contain everything we need to
    # do the various compiles


    shell_env_args_conf = copy(userjobconfig.shell_env_args)
    shell_env_args_conf['CONFIG'] = design_name
    cpp_emu_name = 'emulator-' + userjobconfig.MODEL + '-' + design_name
    vsim_emu_name = 'simv-' + userjobconfig.MODEL + '-' + design_name

    # make C++ emulator
    # NOTE: This is currently required to get the dramsim2_ini directory
    # and get list of tests to run
    # TODO: do we need to get list of tests to run per environment?
    with lcd(rc_dir + '/emulator'), shell_env(**shell_env_args_conf):
        rl2.local_logged('make ' + cpp_emu_name + ' 2>&1')
        rl.local_logged('cp -Lr ../emulator ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/emulator/')

    testslist = read_tests(rc_dir + '/emulator/generated-src/', design_name)

    print("running tests:")
    print(testslist)

    #TODO: run C++ emulator tests

    """ Run vsim """
    if 'vsim' in userjobconfig.tests:
        # make vsim, copy
        with lcd(rc_dir + '/vsim'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            rl2.local_logged('make ' + vsim_emu_name + ' 2>&1')
            rl.local_logged('cp -Lr ../vsim ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vsim/')

        # copy dramsim2_ini directory for vsim
        with lcd(userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name):
            rl.local_logged('cp -r emulator/emulator/dramsim2_ini vsim/vsim/')

        # start vsim tasks
        for y in testslist:
            rs.add(vsimtest.delay(design_name, y, jobinfo, userjobconfig))


    """ Run vcs-sim-rtl """
    if 'vcs-sim-rtl' in userjobconfig.tests:
        # make vcs-sim-rtl, copy
        with lcd(rc_dir + '/vlsi/vcs-sim-rtl'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            rl2.local_logged('make ' + vsim_emu_name + ' 2>&1')
            rl.local_logged('cp -Lr ../vcs-sim-rtl ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-rtl/')

        # copy dramsim2_ini directory for vcs-sim-rtl
        with lcd(userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name):
            rl.local_logged('cp -r emulator/emulator/dramsim2_ini vcs-sim-rtl/vcs-sim-rtl/')

        for y in testslist:
            rs.add(vcs_sim_rtl_test.delay(design_name, y, jobinfo, userjobconfig))

    """ run dc-syn """
    if 'dc-syn' in userjobconfig.tests:
        with lcd(rc_dir + '/vlsi'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            rl2.local_logged('make 2>&1')
        # vlsi, dc
        with lcd(rc_dir + '/vlsi/dc-syn'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            rl2.local_logged('make -j4 2>&1')
            rl.local_logged('cp -r current-dc/reports ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/dc-syn/')
            rl.local_logged('cp -r current-dc/results ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/dc-syn/')

    #with lcd(rc_dir + '/vlsi/vcs-sim-gl-syn'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
    #    # todo actually use the name
    #    rl2.local_logged('make 2>&1')
    #    # todo copy

    rl.clear_log() # clear the redis log list
    if userjobconfig.enableEMAIL:
        email_user(userjobconfig, jobinfo, design_name)
    return rs


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


def vsim(design_name, test_to_run, jobinfo, userjobconfig):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    workdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vsim/vsim'
    with lcd(workdir), shell_env(**userjobconfig.shell_env_args), settings(warn_only=True):
        res = local(samplevcs.format(design_name, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        q = local("tail -n 1 ../{}.out".format(test_to_run), capture=True)
        # return "PASS" and # of cycles
        return ["PASS", q.stdout.split()[1]]

# 5 min timeout per test
@app.task(bind=True, soft_time_limit=300)
def vsimtest(self, design_name, testname, jobinfo, userjobconfig):
    try:
        rval = execute(vsim, design_name, testname, jobinfo, userjobconfig).values()
        return rval
    except SoftTimeLimitExceeded:
        return "FAILED RAN OUT OF TIME"

samplevcs_sim_rtl = 'cd . && ./simv-Top-{} -q +ntb_random_seed_automatic +dramsim +verbose +max-cycles=100000000 +loadmem=../../../../esp-tests/isa/{}.hex 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/hwacha-rv/bin/spike-dasm  > ../{}.out && [ $PIPESTATUS -eq 0 ]'

def vcs_sim_rtl(design_name, test_to_run, jobinfo, userjobconfig):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    workdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-rtl/vcs-sim-rtl'
    with lcd(workdir), shell_env(**userjobconfig.shell_env_args), settings(warn_only=True):
        res = local(samplevcs_sim_rtl.format(design_name, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        q = local("tail -n 1 ../{}.out".format(test_to_run), capture=True)
        # return "PASS" and # of cycles
        return ["PASS", q.stdout.split()[1]]

# 5 min timeout per test
@app.task(bind=True, soft_time_limit=300)
def vcs_sim_rtl_test(self, design_name, testname, jobinfo, userjobconfig):
    try:
        rval = execute(vcs_sim_rtl, design_name, testname, jobinfo, userjobconfig).values()
        return rval
    except SoftTimeLimitExceeded:
        return "FAILED RAN OUT OF TIME"

