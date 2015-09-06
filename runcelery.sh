#!/bin/sh

celery -A tasks worker --loglevel=info -n a8one
