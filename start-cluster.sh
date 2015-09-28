#!/bin/sh
fab -f start-cluster.py celery_master celery_worker celery_flower waiter celery_shutdown cleanup
