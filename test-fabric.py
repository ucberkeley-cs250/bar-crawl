### ONLY RUN THIS ON a8 ###


## todo, maybe modify this to launch from local machine: 
## but issues when laptop loses net

from fabric.api import *

# list of hosts to run remote commands on
fast = ['a7', 'a8', 'a5', 'a6']
med = ['boxboro', 'sandy', 'bridge', 'jktqos', 'jktgz', 'a20', 'a19']

very_slow = ['emerald']
no_ecad = ['beckton']

#env.hosts = fast #+ med
#env.hosts = ['f1']
env.hosts = fast

def celery_master():
    """ Celery master needs to launch redis, flower """
    with lcd('/nscratch/sagark/celery-distr/celery-test'):
        local('uname -a')
        local('redis-server /nscratch/sagark/celery-distr/redis/redis.conf')
        local('ps -A | grep redis-server')
        ##### TODO: need to start flower after all the workers join
        ##### otherwise it doesn't notice them
        local('screen -A -m -d -S flower flower -A tasks --port=8080 &')

import random
import string

#@parallel
def celery_worker():
    with settings(warn_only=True):
        with cd('/nscratch/sagark/celery-distr/celery-test'):
            # we should use -Ofair
            # see http://docs.celeryproject.org/en/latest/userguide/optimizing.html#prefork-pool-prefetch-settings
            # some tests may run for a long time
            if env.host_string in fast:
                run('celery multi start 1.%h 2.%h 3.%h 4.%h 5.%h 6.%h -A tasks --loglevel=info -Ofair -P processes -c 2')
            else:
                run('celery multi start 1.%h -A tasks --loglevel=info -Ofair -P processes -c 1')




def waiter():
    raw_input("Press Enter to continue...")


@parallel
def celery_shutdown():
    with settings(warn_only=True):
        with cd('/nscratch/sagark/celery-distr/celery-test'):
            run('celery multi kill 1.%h 2.%h 3.%h 4.%h')
            run('pkill python')
            run('pkill celery')

def cleanup():
    """ Kill flower """
    local('pkill flower')
    pass
