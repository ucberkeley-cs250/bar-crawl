### ONLY RUN THIS ON a8 ###


## todo, maybe modify this to launch from local machine: 
## but issues when laptop loses net

from fabric.api import *

# list of hosts to run remote commands on
env.hosts = ['a6', 'a7', 'a8', 'boxboro', 'sandy', 'bridge', 'jktqos', 'jktgz', 'a20']


no_ecad = ['beckton']
slow = ['emerald']
people = ['a5']
somepeople = ['a19']

#env.hosts += slow
env.hosts += somepeople

env.hosts = ['a8', 'a7', 'a6', 'a5']

def celery_master():
    """ Celery master needs to launch redis, flower """
    with lcd('/nscratch/sagark/celery-distr/celery-test'):
        local('uname -a')
        local('redis-server /nscratch/sagark/celery-distr/redis/redis.conf')
        local('ps -A | grep redis-server')
        ##### TODO: need to start flower after all the workers join
        ##### otherwise it doesn't notice them
        local('screen -A -m -d -S flower flower -A tasks --port=8080 &')

@parallel
def celery_worker():
    with settings(warn_only=True):
        with cd('/nscratch/sagark/celery-distr/celery-test'):
            # we should use -Ofair
            # see http://docs.celeryproject.org/en/latest/userguide/optimizing.html#prefork-pool-prefetch-settings
            # some tests may run for a long time
            run('celery -A tasks worker --loglevel=fatal -Ofair -c 12')

def cleanup():
    """ Kill flower """
    local('pkill flower')
