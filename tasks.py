import redis
import re
import os

from celery import Celery, Task
from celery.result import ResultSet
from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import task_revoked
from crawlutils import *
from fabric.api import *
from fabric.tasks import execute
from copy import copy

app = Celery('tasks', backend='rpc://', broker=redis_conf_string)
app.conf.CELERY_TIMEZONE = 'America/Los_Angeles'
app.conf.CELERY_ACKS_LATE = True
app.conf.CELERYD_PREFETCH_MULTIPLIER = 1
# because we use late_acks, this must be set to a large value, longer than
# the length of the longest task. set to 2 days here:
app.conf.BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600 * 24 * 2}

class DebTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if args[3].enableEMAIL:
            email_failure(args[3], args[2], args[0], self.request.hostname, einfo)
        pass

    def on_success(self, retval, task_id, args, kwargs):
        if args[3].enableEMAIL:
            email_success(args[3], args[2], args[0], self.request.hostname)
        return

@app.task(bind=True, base=DebTask)
def compile_and_copy(self, design_name, hashes, jobinfo, userjobconfig):
    if userjobconfig.enableEMAIL:
        email_start(userjobconfig, jobinfo, design_name, self.request.hostname)

    rs = ResultSet([])

    rl = RedisLogger(design_name, jobinfo, userjobconfig.logging_on)
    rl2 = RedisLoggerStream(design_name, jobinfo, userjobconfig.logging_on)

    #isfbox = re.match("^f[0-9][0-9]+", self.request.hostname)
    #isfbox = isfbox is not None

    base_dir = "/scratch/"
    #if isfbox:
    #    base_dir = "/data/"
    # create scratch space on this node for compiling the design, then clone
    # for now, do not delete the scratch space, just keep making new ones
    # 1) preserve work dir for debugging
    # 2) let a user run multiple jobs at once
    design_dir = base_dir + userjobconfig.username + '/celery-temp/' + jobinfo + "/" + design_name
    # remove old results for that design if they exist
    #rl.local_logged('rm -rf ' + design_dir)
    rl.local_logged('mkdir -p ' + design_dir)
    with lcd(design_dir):
        rl.local_logged('git clone ' + userjobconfig.rocket_chip_location + " rocket-chip")
    rc_dir = design_dir + '/rocket-chip'
    with lcd(rc_dir):
        # checkout the correct hash
        rl.local_logged('git checkout ' + hashes['rocket-chip'])
        rl.local_logged('git submodule update --init')
        # copy designs scala file
        configs_dir = 'src/main/scala/config'
        rl.local_logged('mkdir -p ' + configs_dir)
        rl.local_logged('cp ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + userjobconfig.CONF + '.scala ' + configs_dir + '/')
        rl.local_logged('rm -rf vlsi')
        rl.local_logged('cp -R /scratch/%s/%s vlsi' % (userjobconfig.username, userjobconfig.vlsi_dir))

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
    if 'emulator' in userjobconfig.tests:
        with lcd(rc_dir + '/emulator'), shell_env(**shell_env_args_conf):
            rl2.local_logged('make ' + cpp_emu_name + ' 2>&1')
    else:
        with lcd(rc_dir + '/emulator'), shell_env(**shell_env_args_conf), settings(warn_only=True):
            # even if emulator is broken, need dramsim
            rl2.local_logged('make ' + cpp_emu_name + ' 2>&1')

    with lcd(rc_dir + '/emulator'), shell_env(**shell_env_args_conf):
        rl.local_logged('cp -Lr ../emulator ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/emulator/')

    testslist = read_tests(rc_dir + '/emulator/generated-src/', design_name)

    print("running tests:")
    print(testslist)
    
    """ Run C++ emulator """
    if 'emulator' in userjobconfig.tests:
        for y in testslist:
            rs.add(emulatortest.apply_async([design_name, y, jobinfo, userjobconfig], queue='test'))


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
            rs.add(vsimtest.apply_async([design_name, y, jobinfo, userjobconfig], queue='test'))


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
            rs.add(vcs_sim_rtl_test.apply_async([design_name, y, jobinfo, userjobconfig], queue='test'))

    """ run dc-syn """
    if 'dc-syn' in userjobconfig.tests:
        with lcd(rc_dir + '/vlsi'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            rl2.local_logged('make dc 2>&1')
        # vlsi, dc
        #with lcd(rc_dir + '/vlsi/dc-syn'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
        #    # TODO: what does -jN do here?
        #    #rl2.local_logged('make 2>&1')
        #    rl.local_logged('cp -r current-dc/reports ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/dc-syn/')
        #    rl.local_logged('cp -r current-dc/results ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/dc-syn/')

    rl.clear_log() # if we made it this far, clear the redis log list

    if 'vcs-sim-gl-syn' in userjobconfig.tests:
        with lcd(rc_dir + '/vlsi/vcs-sim-gl-syn'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            # todo actually use the name
            rl2.local_logged('make 2>&1')
            # todo copy
            rl.local_logged('cp -Lr ../vcs-sim-gl-syn ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-gl-syn/')
        # copy dramsim2_ini directory for vcs-sim-gl-syn
        with lcd(userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name):
            rl.local_logged('cp -r emulator/emulator/dramsim2_ini vcs-sim-gl-syn/vcs-sim-gl-syn/')

        for y in testslist:
            rs.add(vcs_sim_gl_syn_test.apply_async([design_name, y, jobinfo, userjobconfig], queue='test'))

    """ run icc-par """
    if 'icc-par' in userjobconfig.tests:
        with lcd(rc_dir + '/vlsi'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            rl2.local_logged('make icc 2>&1')
        # vlsi, icc
        #with lcd(rc_dir + '/vlsi/icc-par'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
        #    # TODO: what does -jN do here?
        #    #rl2.local_logged('make 2>&1')
        #    rl.local_logged('cp -r current-icc/reports ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/icc-par/')
        #    rl.local_logged('cp -r current-icc/results ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/icc-par/')

    if 'vcs-sim-gl-par' in userjobconfig.tests:
        with lcd(rc_dir + '/vlsi/vcs-sim-gl-par'), shell_env(**shell_env_args_conf), prefix('source ' + vlsi_bashrc):
            # todo actually use the name
            rl2.local_logged('make 2>&1')
            # todo copy
            rl.local_logged('cp -Lr ../vcs-sim-gl-par ' + userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-gl-par/')
        # copy dramsim2_ini directory for vcs-sim-gl-par
        with lcd(userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name):
            rl.local_logged('cp -r emulator/emulator/dramsim2_ini vcs-sim-gl-par/vcs-sim-gl-par/')

        for y in testslist:
            rs.add(vcs_sim_gl_par_test.apply_async([design_name, y, jobinfo, userjobconfig], queue='test'))

    rl.clear_log() # clear the redis log list

    return rs

sampleemulator = "./emulator-Top-{} +dramsim +max-cycles=100000000 +verbose +loadmem={}/tests-installs/{}/{}/{}.hex none 2>&1 | spike-dasm --extension=hwacha > ../{}.out && [ $PIPESTATUS -eq 0 ]"


def extract_cycles(test_type, test_to_run):
    if "benchmarks" in test_type:
        q = local("grep -r 'cycle = ' ../{}.out".format(test_to_run), capture=True)
        cyclecount = q.split("=")[1].strip()
    else:
        q = local("grep -r 'C0: ' ../{}.out | tail -n 1".format(test_to_run), capture=True)
        cyclecount = q.stdout.split()[1]
    return cyclecount


def emulator(design_name, test_to_run, jobinfo, userjobconfig):
    """ run a test """
    workdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/emulator/emulator'
    test_type, test_to_run = split_test_name(test_to_run)
    with lcd(workdir), shell_env(**userjobconfig.shell_env_args), settings(warn_only=True):
        res = local(sampleemulator.format(design_name, userjobconfig.install_dir, userjobconfig.hashes['riscv-tests'], test_type, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        cyclecount = extract_cycles(test_type, test_to_run)
        # return "PASS" and # of cycles
        return ["PASS", cyclecount]

# 5 min timeout per test
@app.task(bind=True, soft_time_limit=3600*24)
def emulatortest(self, design_name, testname, jobinfo, userjobconfig):
    try:
        rval = execute(emulator, design_name, testname, jobinfo, userjobconfig).values()
        return rval
    except SoftTimeLimitExceeded:
        return limit_exceeded()

samplevcs = "cd . && ./simv-Top-{} -q +ntb_random_seed_automatic +dramsim +verbose +max-cycles=100000000 +loadmem={}/tests-installs/{}/{}/{}.hex 2>&1 | spike-dasm --extension=hwacha > ../{}.out && [ $PIPESTATUS -eq 0 ]"

def vsim(design_name, test_to_run, jobinfo, userjobconfig):
    """ run a test """
    workdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vsim/vsim'
    test_type, test_to_run = split_test_name(test_to_run)

    with lcd(workdir), shell_env(**userjobconfig.shell_env_args), settings(warn_only=True):
        res = local(samplevcs.format(design_name, userjobconfig.install_dir, userjobconfig.hashes['riscv-tests'], test_type, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        cyclecount = extract_cycles(test_type, test_to_run)
        # return "PASS" and # of cycles
        return ["PASS", cyclecount]

# 5 min timeout per test
@app.task(bind=True, soft_time_limit=3600*24)
def vsimtest(self, design_name, testname, jobinfo, userjobconfig):
    try:
        rval = execute(vsim, design_name, testname, jobinfo, userjobconfig).values()
        return rval
    except SoftTimeLimitExceeded:
        return limit_exceeded()

samplevcs_sim_rtl = 'cd . && ./simv-Top-{} -q +ntb_random_seed_automatic +dramsim +verbose +max-cycles=100000000 +loadmem={}/tests-installs/{}/{}/{}.hex 2>&1 | spike-dasm --extension=hwacha > ../{}.out && [ $PIPESTATUS -eq 0 ]'

def vcs_sim_rtl(design_name, test_to_run, jobinfo, userjobconfig):
    """ run a test """
    workdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-rtl/vcs-sim-rtl'
    test_type, test_to_run = split_test_name(test_to_run)
    with lcd(workdir), shell_env(**userjobconfig.shell_env_args), settings(warn_only=True):
        res = local(samplevcs_sim_rtl.format(design_name, userjobconfig.install_dir, userjobconfig.hashes['riscv-tests'], test_type, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        cyclecount = extract_cycles(test_type, test_to_run)
        # return "PASS" and # of cycles
        return ["PASS", cyclecount]

# 5 min timeout per test
@app.task(bind=True, soft_time_limit=3600*24)
def vcs_sim_rtl_test(self, design_name, testname, jobinfo, userjobconfig):
    try:
        rval = execute(vcs_sim_rtl, design_name, testname, jobinfo, userjobconfig).values()
        return rval
    except SoftTimeLimitExceeded:
        return limit_exceeded()


samplevcs_sim_gl_syn = "cd . && ./simv-{} -ucli -do +run.tcl +dramsim +verbose +max-cycles=100000000 +loadmem={}/tests-installs/{}/{}/{}.hex 2>&1 | spike-dasm --extension=hwacha > ../{}.out && [ $PIPESTATUS -eq 0 ]"

def vcs_sim_gl_syn(design_name, test_to_run, jobinfo, userjobconfig):
    """ run a test """
    workdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-gl-syn/vcs-sim-gl-syn'
    test_type, test_to_run = split_test_name(test_to_run)
    with lcd(workdir), shell_env(**userjobconfig.shell_env_args), prefix('source ' + vlsi_bashrc), settings(warn_only=True):
        res = local(samplevcs_sim_gl_syn.format(design_name,userjobconfig.install_dir, userjobconfig.hashes['riscv-tests'], test_type, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        cyclecount = extract_cycles(test_type, test_to_run)
        # return "PASS" and # of cycles
        return ["PASS", cyclecount]

# no time-limit on gl-syn
@app.task(bind=True)
def vcs_sim_gl_syn_test(self, design_name, testname, jobinfo, userjobconfig):
    try:
        rval = execute(vcs_sim_gl_syn, design_name, testname, jobinfo, userjobconfig).values()
        return rval
    except SoftTimeLimitExceeded:
        return limit_exceeded()


samplevcs_sim_gl_par = "cd . && ./simv-{} -ucli -do +run.tcl +dramsim +verbose +max-cycles=100000000 +loadmem={}/tests-installs/{}/{}/{}.hex 2>&1 | spike-dasm --extension=hwacha > ../{}.out && [ $PIPESTATUS -eq 0 ]"

def vcs_sim_gl_par(design_name, test_to_run, jobinfo, userjobconfig):
    """ run a test """
    workdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo + '/' + design_name + '/vcs-sim-gl-par/vcs-sim-gl-par'
    test_type, test_to_run = split_test_name(test_to_run)
    with lcd(workdir), shell_env(**userjobconfig.shell_env_args), prefix('source ' + vlsi_bashrc), settings(warn_only=True):
        res = local(samplevcs_sim_gl_par.format(design_name,userjobconfig.install_dir, userjobconfig.hashes['riscv-tests'], test_type, test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        cyclecount = extract_cycles(test_type, test_to_run)
        # return "PASS" and # of cycles
        return ["PASS", cyclecount]

# no time-limit on gl-par
@app.task(bind=True)
def vcs_sim_gl_par_test(self, design_name, testname, jobinfo, userjobconfig):
    try:
        rval = execute(vcs_sim_gl_par, design_name, testname, jobinfo, userjobconfig).values()
        return rval
    except SoftTimeLimitExceeded:
        return limit_exceeded()


def limit_exceeded():
    kill_child_processes(os.getpid())
    return "FAILED RAN OUT OF TIME " + str(os.getpid())


@task_revoked.connect
def task_revoked_handler(request, terminated, signum, expired, **kwargs):
    # kill child tasks on revoke
    kill_child_processes(request.worker_pid)


