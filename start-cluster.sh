#!/bin/sh
fab -f start-cluster.py celery_master celery_worker one_host celery_flower waiter restore_hosts celery_shutdown cleanup
