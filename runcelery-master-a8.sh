#!/bin/sh

# requires that redis.conf contains daemonize yes
redis-server /nscratch/sagark/celery-distr/redis/redis.conf
ps -A | grep redis-server
celery -A tasks worker --loglevel=info -n a8one
