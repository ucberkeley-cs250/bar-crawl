#!/bin/sh
fab -f test-fabric.py celery_master celery_worker waiter celery_shutdown cleanup
