#!/bin/sh
fab -f clusterman.py celery_master celery_worker one_host celery_flower
