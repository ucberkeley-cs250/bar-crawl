import subprocess
import redis
from fabric.api import *
from fabric import operations
import sys



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

