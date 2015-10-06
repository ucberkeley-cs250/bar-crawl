import subprocess
import redis
from fabric.api import *
from fabric import operations
import sys

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


    # we ignore benchmarks for now, which are in other:
    return asm_tests

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
        'host': 'a8.millennium.berkeley.edu',
        'port': 6379,
        'db': 0
}
redis_conf_string = 'redis://' + redis_conf['host'] + ":" + str(redis_conf['port'])

class RedisLogger:
    def __init__(self, design_name):
        self.red = redis.StrictRedis(**redis_conf)
        self.design_name = design_name

    def local_logged(self, cmd):
        self.red.lpush(self.design_name, '> ' + cmd + '\n')
        self.red.publish(self.design_name, '> ' + cmd + '\n')
        r = local(cmd, capture=True)
        self.red.lpush(self.design_name, "stdout:\n" + r.stdout + '\n')
        self.red.publish(self.design_name, "stdout:\n" + r.stdout + '\n')
        self.red.lpush(self.design_name, "stderr:\n" + r.stderr + '\n')
        self.red.publish(self.design_name, "stderr:\n" + r.stderr + '\n')

    def clear_log(self):
        self.red.delete(self.design_name)

class RedisLoggerStream:
    """ Replace fabric local to allow for streaming output back to the master
    through redis.

    This is experimental since it uses internal functions from fabric. Use
    only for non-destructive stuff for now just to be safe.
    """
    def __init__(self, design_name):
        self.red = redis.StrictRedis(**redis_conf)
        self.design_name = design_name

    def local_logged(self, cmd):
        with_env = operations._prefix_env_vars(cmd, local=True)
        wrapped_command = operations._prefix_commands(with_env, 'local')
        self.red.lpush(self.design_name, '> ' + wrapped_command + '\n')
        self.red.publish(self.design_name, '> ' + wrapped_command + '\n')
        s = subprocess.Popen(wrapped_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                executable=None, close_fds=True)
        for c in iter(lambda: s.stdout.read(1), ''):
            self.red.publish(self.design_name, c)
            self.red.lpush(self.design_name, c)

    def clear_log(self):
        self.red.delete(self.design_name)

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
        f.write("\n".join(actualdiff) + "\n")
        f.close()
        print "----"

        with lcd(apply_to_dir + "/" + relative_path):
            local('git apply ' + tempfile)


def email_user(userjobconfig, jobinfo, design_name):
    outputdir = userjobconfig.distribute_rocket_chip_loc + '/' + jobinfo 
    cmdstr = """curl -s --user 'api:{}' \
    https://api.mailgun.net/v3/bar-crawl.sagark.org/messages \
    -F from='bar-crawl <mailgun@bar-crawl.sagark.org>' \
    -F to={} \
    -F to={} \
    -F subject='bar-crawl: Design {} in Job {} has Completed' \
    -F text='Design {} for job {} has completed!\nYou can find results in: {}'""".format(
            userjobconfig.mailgun_api, userjobconfig.email_addr, 
            userjobconfig.cc_addr, design_name, jobinfo, design_name, jobinfo,  outputdir + 
            '/' + design_name)
    local(cmdstr)

