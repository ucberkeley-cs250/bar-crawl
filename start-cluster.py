""" Start up the cluster. Run from the master node. """

from fabric.api import *
import time
import os
import random
import string


# list of hosts to run remote commands on
fast = ['a7', 'a8', 'a5', 'a6']
med = ['boxboro', 'sandy', 'bridge', 'jktqos', 'jktgz', 'a20', 'a19']

very_slow = ['emerald']
no_ecad = ['beckton']

env.hosts = fast
backuphosts = env.hosts

bar_crawl_dir = os.getcwd()
redis_install = '/nscratch/sagark/celery-distr/redis/redis.conf'

def celery_master():
    """ Celery master needs to launch redis, flower """
    with lcd(bar_crawl_dir):
        local('uname -a')
        local('redis-server ' + redis_install)
        local('ps -A | grep redis-server')


def celery_worker():
    with settings(warn_only=True):
        # distribute data to the node
        with cd(bar_crawl_dir):
            # we should use -Ofair
            # see http://docs.celeryproject.org/en/latest/userguide/optimizing.html#prefork-pool-prefetch-settings
            # some tests may run for a long time
            if env.host_string in fast:
                run('celery multi start 1.%h -A tasks --purge --loglevel=info -Ofair -P processes -c 12')
            else:
                run('celery multi start 1.%h -A tasks --purge --loglevel=info -Ofair -P processes -c 1')


def celery_flower():
    with lcd(bar_crawl_dir):
        print("waiting 5s for workers to settle")
        time.sleep(5)
        local('screen -A -m -d -S flower flower -A tasks --port=8080 &')

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
            run('celery multi kill 1.%h 2.%h 3.%h 4.%h')
            run('pkill python')
            run('pkill celery')

def cleanup():
    """ Kill flower """
    local('pkill flower')
    pass