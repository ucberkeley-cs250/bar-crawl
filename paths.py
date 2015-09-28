""" Directory structure:
in /nscratch/sagark/celery-workspace:
distribute/date-time-commit8/
    -Designs.scala
    -Design0
    -Design1
    -Design2
        -emulator (C++)
        -vsim
        -etc
-------------- 
exec flow:

    1) Master on /scratch/sagark/hwacha-celery/rocket-chip
        a) runs jackhammer to generate rocket-chip/src/main/scala/configs/Designs.scala
        b) Copy Designs.scala to /nscratch/sagark/celery-workspace/distribute/
        c) Run distributed compile jobs for each design
            Arg to each compile task is just design name (like Design0)

            1) mkdir /scratch/sagark/celery-temp/design-name && cd there
            2) git clone git@github.com:sagark/rocket-chip
            3) cd rocketchip && git submodule update --init
            4) copy Designs.scala from /nscratch/sagark/celery-workspace/distribute/
                to src/main/scala/configs/
            5) Run compile jobs for emulator, vsim, etc
                Copy to 
                /nscratch/sagark/celery-workspace/distribute/DesignN/[test type]
            6) Start subtasks to run tests

"""
import subprocess
import redis
from fabric.api import *
from fabric import operations
import sys

# location of your code on scratch on the master node
# -celery will run based on the latest commit here
# -make sure you've pushed to github
master_rocket_chip_dir = "/scratch/sagark/hwacha-celery/rocket-chip"

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

# TODO need to figure out a way to make this check against riscv-tools hash
# probably need to make the riscv-tools installer store the repo url/hash
# somewhere in $RISCV

# risc-v tools installation. should be on nscratch
rvenv = "/nscratch/sagark/celery-workspace/hwacha-rv"
env_RISCV = rvenv
env_PATH = rvenv+"/bin:$PATH"
env_LD_LIBRARY = rvenv+"/lib"

MODEL='Top'
CONF = 'EOS24Config' # this is the overall config name (as opposed to EOS24Config0, EOS24Config1, etc)

rocket_chip_location = 'git@github.com:sagark/rocket-chip'
tests_location = 'git@github.com:ucb-bar/esp-tests.git'

distribute_rocket_chip_loc = "/nscratch/sagark/celery-workspace/distribute"

vlsi_bashrc = '/ecad/tools/vlsi.bashrc'

shell_env_args = {
        'RISCV': env_RISCV,
        'PATH': env_PATH,
        'LD_LIBRARY_PATH': env_LD_LIBRARY,
        'CONFIG': CONF
}

broker = 'redis://boxboro.millennium.berkeley.edu:6379'

redis_conf = {
        'host': 'boxboro.millennium.berkeley.edu',
        'port': 6379,
        'db': 0
}

redis_conf_string = 'redis://' + redis_conf['host'] + ":" + str(redis_conf['port'])

tests = ['emulator', 'vsim', 'vcs-sim-rtl']

class Catcher(object):
    def __init__(self, design_name, red):
        self.red = red
        self.design_name = design_name

    def write(self, msg):
        self.red.lpush(self.design_name, msg)
        self.red.publish(self.design_name, msg)
    
    def flush(self):
        pass

class RedisLogger:
    def __init__(self, design_name):
        self.red = redis.StrictRedis(**redis_conf)
        self.design_name = design_name
        self.override = Catcher(design_name, self.red) 
        self.bkupstdout = sys.stdout
        self.bkupstderr = sys.stderr

    def local_logged(self, cmd):
        self.red.lpush(self.design_name, '> ' + cmd + '\n')
        self.red.publish(self.design_name, '> ' + cmd + '\n')
        #sys.stdout = self.override
        #sys.stderr = self.override
        r = local(cmd, capture=True)
        #sys.stdout = self.bkupstdout
        #sys.stderr = self.bkupstderr
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
        self.override = Catcher(design_name, self.red) 
        self.bkupstdout = sys.stdout
        self.bkupstderr = sys.stderr

    def local_logged(self, cmd):
        with_env = operations._prefix_env_vars(cmd, local=True)
        wrapped_command = operations._prefix_commands(with_env, 'local')



        self.red.lpush(self.design_name, '> ' + wrapped_command + '\n')
        self.red.publish(self.design_name, '> ' + wrapped_command + '\n')
        #sys.stdout = self.override
        #sys.stderr = self.override
        #r = local(cmd, capture=True)
        s = subprocess.Popen(wrapped_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                executable=None, close_fds=True)
        for c in iter(lambda: s.stdout.read(1), ''):
            self.red.publish(self.design_name, c)
            self.red.lpush(self.design_name, c)
        #sys.stdout = self.bkupstdout
        #sys.stderr = self.bkupstderr
        #self.red.lpush(self.design_name, "stdout:\n" + r.stdout + '\n')
        #self.red.publish(self.design_name, "stdout:\n" + r.stdout + '\n')
        #self.red.lpush(self.design_name, "stderr:\n" + r.stderr + '\n')
        #self.red.publish(self.design_name, "stderr:\n" + r.stderr + '\n')

    def clear_log(self):
        self.red.delete(self.design_name)

