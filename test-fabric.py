### ONLY RUN THIS ON a8 ###


## todo, maybe modify this to launch from local machine: 
## but issues when laptop loses net

from fabric.api import *

# list of hosts to run remote commands on
env.hosts = ['a7', 'boxboro', 'emerald', 'beckton', 'sandy', 'bridge']

def celery_master():
    """ Celery master needs to launch redis, flower """
    with lcd('/nscratch/sagark/celery-distr/celery-test'):
        local('uname -a')
        local('redis-server /nscratch/sagark/celery-distr/redis/redis.conf')
        local('ps -A | grep redis-server')
        local('screen -A -m -d -S flower flower -A tasks --port=8080 &')

@parallel
def celery_worker():
    with cd('/nscratch/sagark/celery-distr/celery-test'):
        run('celery -A tasks worker --loglevel=info')
