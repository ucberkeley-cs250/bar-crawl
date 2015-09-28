import subprocess
import redis
from fabric.api import *
from fabric import operations
import sys


""" USER CONFIG. Need to wrap this up and send to subtasks """
# location of your code on scratch on the master node
# -celery will run based on the latest commit here
# -make sure you've pushed to github
master_rocket_chip_dir = "/scratch/sagark/hwacha-celery/rocket-chip"

# risc-v tools installation. should be on nscratch
rvenv = "/nscratch/sagark/celery-workspace/hwacha-rv"
env_RISCV = rvenv
env_PATH = rvenv+"/bin:$PATH"
env_LD_LIBRARY = rvenv+"/lib"

MODEL='Top'
CONF = 'EOS24Config' # this is the overall config name (as opposed to EOS24Config0, EOS24Config1, etc)

shell_env_args = {
        'RISCV': env_RISCV,
        'PATH': env_PATH,
        'LD_LIBRARY_PATH': env_LD_LIBRARY,
        'CONFIG': CONF
}

rocket_chip_location = 'git@github.com:sagark/rocket-chip'
tests_location = 'git@github.com:ucb-bar/esp-tests.git'

# this should probably be set on a per-project basis
distribute_rocket_chip_loc = "/nscratch/sagark/celery-workspace/distribute"

# set of tests to run
# TODO: use these inside compile_and_copy to decide what to actually run
tests = ['emulator', 'vsim', 'vcs-sim-rtl', 'dc-syn']


""" Utils/Globals below"""
def get_hash(p):
    """ Get HEAD commit hash given full repo path."""
    with lcd(p):
        h = local('git rev-parse HEAD', capture=True)
    return h.stdout

def get_hashes():
    """ Populate a dictionary full of commit hashes for components."""
    # submodule paths relative to rocket-chip root. 
    submodules = ['riscv-tools', 'riscv-tools/riscv-tests']
    submodule_paths = map(lambda x: master_rocket_chip_dir + '/' + x, submodules)
    d = {}
    d['rocket-chip'] = get_hash(master_rocket_chip_dir)
    for x in submodule_paths:
        d[x.rsplit('/', 1)[-1]] = get_hash(x)
    return d

vlsi_bashrc = '/ecad/tools/vlsi.bashrc'

# this is the redis server that is used by celery/flower and the watch mechanism
# it's a good idea to put this on a machine with lots of RAM
redis_conf = {
        'host': 'boxboro.millennium.berkeley.edu',
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

