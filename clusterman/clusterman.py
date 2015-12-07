""" Start up the cluster. Run from the master node. """
from fabric.api import *
import time
import os, sys
import random
import string

#parentdir = os.path.dirname(__file__)
sys.path.insert(0,'..')

from crawlutils import get_hash

# list of hosts to run remote commands on
abuild = ['a1', 'a2']
fast = ['a7', 'a8', 'a5', 'a6']
noa7fast = ['a8', 'a5', 'a6']
med = ['boxboro', 'sandy', 'bridge', 'jktqos', 'jktgz', 'a20', 'a19']

fbox = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12', 'f13', 'f14', 'f15', 'f16']
#fbox = ['f15']

very_slow = ['emerald']
no_ecad = ['beckton']

env.hosts = abuild
#env.hosts = fbox
backuphosts = env.hosts

bar_crawl_dir = os.getcwd() + "/.."
redis_install = os.getcwd() + "/redis.conf"

# prefix worker name with hash of current version of bar-crawl to keep things
# consistent for users
h = get_hash(bar_crawl_dir)[:8]

def celery_master():
    """ Celery master needs to launch redis """
    with lcd(bar_crawl_dir):
        local('uname -a')
        local('redis-server ' + redis_install)
        local('ps -A | grep redis-server')


pidfilename_build = 'clusterman/pid/build-' + h + '%h.pid'
logfilename_build = 'clusterman/log/build-' + h + '%h.log'
pidfilename_test = 'clusterman/pid/test-' + h + '%h.pid'
logfilename_test = 'clusterman/log/test-' + h + '%h.log'

@parallel
def celery_worker():
    with settings(warn_only=True):
        # distribute data to the node
        with cd(bar_crawl_dir):
            # we should use -Ofair
            # see http://docs.celeryproject.org/en/latest/userguide/optimizing.html#prefork-pool-prefetch-settings
            # some tests may run for a long time
            run('celery multi start build-' + h + ' -E --pidfile=' + pidfilename_build +  ' --logfile=' + logfilename_build + ' -Q build -A tasks --purge -l INFO -Ofair -P processes -c 1')
            #run('celery multi start test-' + h + ' -E --pidfile=' + pidfilename_test +  ' --logfile=' + logfilename_test + ' -Q test -A tasks --purge -l INFO -Ofair -P processes -c 6')


def celery_flower():
    with lcd(bar_crawl_dir):
        print("waiting 5s for workers to settle")
        time.sleep(5)
        local('screen -A -m -d -S flower flower -A tasks --port=8888 --persistent &')

def one_host():
    env.hosts = []

def waiter():
    raw_input("Press Enter to continue...")

def restore_hosts():
    env.hosts = backuphosts

@parallel
def celery_shutdown():
    with settings(warn_only=True):
        with cd(bar_crawl_dir):
            run('celery multi stop build-' + h + ' --pidfile=' + pidfilename_build)
            run('celery multi stop test-' + h + ' --pidfile=' + pidfilename_test)
            run('pkill python')
            run('pkill celery')

def flower_shutdown():
    """ Kill flower. Not used currently. """
    with settings(warn_only=True):
        local('pkill flower')
