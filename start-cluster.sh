#!/bin/sh
fab -f test-fabric.py celery_master celery_worker celery_flower waiter celery_shutdown cleanup
