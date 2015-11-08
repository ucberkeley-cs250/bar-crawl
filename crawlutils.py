import subprocess
import redis
from fabric.api import *
from fabric import operations
import sys
import requests
import subprocess
import signal
import os


def split_test_name(type_test):
    return type_test.split('-', 1)

def read_tests(generated_src_dir, design_name):
    """ This will read the tests to run from
        generated_src_dir/Top.design_name.d
    and return a list of tests.

    Currently, it only runs the asm tests.
    """
    f = generated_src_dir + "/Top." + design_name + ".d"
    a = open(f, 'r')
    b = a.readlines()
    a.close()

    equalsmode = False
    is_asm = False
    asm_tests = []
    other_tests = []

    for line in b:
        if equalsmode:
            if line.startswith("\t"):
                if is_asm:
                    asm_tests.append(line.replace("\\", "").strip())
                else:
                    other_tests.append(line.replace("\\", "").strip())
            else:
                equalsmode = False
        if "=" in line:
            equalsmode = True
            if "asm" in line:
                is_asm = True
            else:
                is_asm = False

    asm_tests = map(lambda x: 'isa-' + x, asm_tests)
    other_tests = map(lambda x: 'benchmarks-' + x, other_tests)

    # we ignore benchmarks for now, which are in other:
    return asm_tests + other_tests

""" Utils/Globals below"""
def get_hash(p):
    """ Get HEAD commit hash given full repo path."""
    with lcd(p):
        h = local('git rev-parse HEAD', capture=True)
    return h.stdout

def get_hashes(base_dir):
    """ Populate a dictionary full of commit hashes for components."""
    # submodule paths relative to rocket-chip root. 
    submodules = ['riscv-tools', 'riscv-tools/riscv-tests']
    submodule_paths = map(lambda x: base_dir + '/' + x, submodules)
    d = {}
    d['rocket-chip'] = get_hash(base_dir)
    for x in submodule_paths:
        d[x.rsplit('/', 1)[-1]] = get_hash(x)
    return d

vlsi_bashrc = '/ecad/tools/vlsi.bashrc'

# this is the redis server that is used by celery/flower and the watch mechanism
# it's a good idea to put this on a machine with lots of RAM
redis_conf = {
        'host': 'fbox.millennium.berkeley.edu',
        'port': 6379,
        'db': 0
}
redis_conf_string = 'redis://' + redis_conf['host'] + ":" + str(redis_conf['port'])

class RedisLogger:
    def __init__(self, design_name, jobname, logging_on):
        self.red = redis.StrictRedis(**redis_conf)
        self.design_name = design_name
        self.job_name = jobname
        self.logging_on = logging_on

    def local_logged(self, cmd):
        if not self.logging_on:
            # run without logging
            local(cmd)
            return
        n = self.job_name + "-" + self.design_name
        self.red.lpush(n, '> ' + cmd + '\n')
        self.red.publish(n, '> ' + cmd + '\n')
        r = local(cmd, capture=True)
        self.red.lpush(n, "stdout:\n" + r.stdout + '\n')
        self.red.publish(n, "stdout:\n" + r.stdout + '\n')
        self.red.lpush(n, "stderr:\n" + r.stderr + '\n')
        self.red.publish(n, "stderr:\n" + r.stderr + '\n')

    def clear_log(self):
        n = self.job_name + "-" + self.design_name
        self.red.delete(n)

class RedisLoggerStream:
    """ Replace fabric local to allow for streaming output back to the master
    through redis.

    This is experimental since it uses internal functions from fabric. Use
    only for non-destructive stuff for now just to be safe.
    """
    def __init__(self, design_name, jobname, logging_on):
        self.red = redis.StrictRedis(**redis_conf)
        self.design_name = design_name
        self.job_name = jobname
        self.logging_on = logging_on

    def local_logged(self, cmd):
        if not self.logging_on:
            # run without logging
            local(cmd)
            return
        with_env = operations._prefix_env_vars(cmd, local=True)
        wrapped_command = operations._prefix_commands(with_env, 'local')
        self.red.lpush(self.job_name + "-" + self.design_name, '> ' + wrapped_command + '\n')
        self.red.publish(self.job_name + "-" + self.design_name, '> ' + wrapped_command + '\n')
        s = subprocess.Popen(wrapped_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                executable=None, close_fds=True)
        for c in iter(lambda: s.stdout.read(1), ''):
            self.red.publish(self.job_name + "-" + self.design_name, c)
            self.red.lpush(self.job_name + "-" + self.design_name, c)

    def clear_log(self):
        self.red.delete(self.job_name + "-" + self.design_name)

subdiffendmarker = "END-------------------"

def generate_recursive_patches(master_dir, patch_dir):
    # TODO:
    #  currently does not handle untracked files
    
    # rocket-chip diff
    with lcd(master_dir):
        h = local('git diff > ' + patch_dir + '/rocket-chip.patch', capture=True)

    # submodule diffs
    with lcd(master_dir):
        h = local('git submodule foreach --recursive "git diff; echo \'' + subdiffendmarker + '\'" > ' + patch_dir + '/submodules.patch', capture=True)



def apply_recursive_patches(patch_dir, apply_to_dir):
    # TODO handle case with empty patches
    #
    # rocketchip
    with lcd(apply_to_dir), settings(warn_only=True):
        local('git apply ' + patch_dir + '/rocket-chip.patch')

    # submodules
    # there's probably a better way to do this...
    # build dictionary of diffs
    f = open(patch_dir + '/submodules.patch', 'r')
    d = f.read()
    f.close()

    diffs = {}
    # code lines start with +, -, or a space, so this is okay
    subdiff = d.split("\n" + subdiffendmarker)
    # only keep parts of the output that have a diff output
    #print subdiff
    diffstoprocess = filter(lambda x: "diff" in x, subdiff)
    tempfile = patch_dir + '/apply_sub.patch'
    for diff in diffstoprocess:
        d = diff.strip().split("\n")
        relative_path = d[0].split(" ")[1].replace("'", "")
        print relative_path
        actualdiff = d[1:]
        f = open(tempfile, 'w')
        f.write("\n".join(actualdiff) + "\n\n")
        f.close()
        print "----"

        with lcd(apply_to_dir + "/" + relative_path):
            local('git apply ' + tempfile)


def email_failure(userjobconfig, jobinfo, design_name, hostname, exc):
    emails = userjobconfig.emails
    subj = 'bar-crawl FAILURE: Design {} in Job {} has failed'.format(design_name, jobinfo)
    outputdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo
    msg = """Design {} in job {} has failed.
You can find archived results in: {}

Temporary results are located on: {}
In: /scratch/{}/celery-temp/{}/{}

Below is the additional information you supplied about this job:
----------------------------------------------------------------
{}
----------------------------------------------------------------
Below is the exception if one was generated:
----------------------------------------------------------------
{}
----------------------------------------------------------------

    """.format(design_name, jobinfo, outputdir + '/' + design_name, 
            hostname,
            userjobconfig.username,
            jobinfo,
            design_name,
            userjobconfig.longdescription,
            str(exc))
    return requests.post(
        "https://api.mailgun.net/v3/bar-crawl.sagark.org/messages",
        auth=("api", userjobconfig.mailgun_api),
        data={"from": "bar-crawl <mailgun@bar-crawl.sagark.org>",
              "to": emails,
              "subject": subj,
              "text": msg
              }
        )


def email_success(userjobconfig, jobinfo, design_name, hostname):
    emails = userjobconfig.emails
    subj = 'bar-crawl SUCCESS: Design {} in Job {} has completed'.format(design_name, jobinfo)
    outputdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo
    msg = """Design {} in job {} has completed!
You can find archived results in: {}

Temporary results are located on: {}
In: /scratch/{}/celery-temp/{}/{}

Below is the additional information you supplied about this job:
----------------------------------------------------------------
{}

    """.format(design_name, jobinfo, outputdir + '/' + design_name, 
            hostname,
            userjobconfig.username,
            jobinfo,
            design_name,
            userjobconfig.longdescription)
    return requests.post(
        "https://api.mailgun.net/v3/bar-crawl.sagark.org/messages",
        auth=("api", userjobconfig.mailgun_api),
        data={"from": "bar-crawl <mailgun@bar-crawl.sagark.org>",
              "to": emails,
              "subject": subj,
              "text": msg
              }
        )

def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    ps_command = subprocess.Popen("ps -o pid --ppid %d --noheaders" % parent_pid, shell=True, stdout=subprocess.PIPE)
    ps_output = ps_command.stdout.read()
    retcode = ps_command.wait()
    if retcode != 0: return
    pids = ps_output.strip().split("\n")
    pids = map(lambda x: x.strip(), pids)
    for pid_str in pids:
        try:
            kill_child_processes(int(pid_str), sig)
            os.kill(int(pid_str), sig)
        except OSError: pass



class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
