""" Directory structure:


in /nscratch/sagark/celery-workspace:


distribute/
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
import redis
from fabric.api import *
import sys

# location of your code on scratch on the master node
master_rocket_chip_dir = "/scratch/sagark/hwacha-celery/rocket-chip"

# risc-v tools installation. should be on nscratch
rvenv = "/nscratch/sagark/celery-workspace/hwacha-rv"
env_RISCV = rvenv
env_PATH = rvenv+"/bin:$PATH"
env_LD_LIBRARY = rvenv+"/lib"



MODEL='Top'
CONF = 'HwachaVLSIConfig'

repo_location = 'git@github.com:sagark/rocket-chip'
tests_location = 'git@github.com:ucb-bar/esp-tests.git'

distribute_rocket_chip_loc = "/nscratch/sagark/celery-workspace/distribute"

vlsi_bashrc = '/ecad/tools/vlsi.bashrc'

shell_env_args = {
        'RISCV': env_RISCV,
        'PATH': env_PATH,
        'LD_LIBRARY_PATH': env_LD_LIBRARY
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
        #self.red.lpush(self.design_name, cmd)
        #self.red.publish(self.design_name, cmd)
        sys.stdout = self.override
        sys.stderr = self.override
        r = local(cmd, capture=False)
        sys.stdout = self.bkupstdout
        sys.stderr = self.bkupstderr
        #self.red.lpush(self.design_name, r.stdout)
        #self.red.publish(self.design_name, r.stdout)
        #self.red.lpush(self.design_name, r.stderr)
        #self.red.publish(self.design_name, r.stderr)

    def clear_log(self):
        self.red.delete(self.design_name)

#def gen_logged_local(design_name):
#    """ Generate a version of fabric's local that logs to logf.
#
#    An empty log can be created with make_log above.
#    """
#    def l2(cmd):
#        red.lpush(design_name, cmd)
#        red.publish(design_name, cmd)
#        r = local(cmd, capture=True) 
#        red.lpush(design_name, r.stdout)
#        red.publish(design_name, r.stdout)
#        red.lpush(design_name, r.stderr)
#        red.publish(design_name, r.stderr)
#    return l2
