#!/bin/bash

easy_install --prefix=/nscratch/sagark/py_inst celery[redis]
easy_install --prefix=/nscratch/sagark/py_inst flower


echo "You should manually obtain the source of redis and build/install it in nscratch/sagark/bin"
