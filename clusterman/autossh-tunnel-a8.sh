#!/bin/sh

# port forward to access the web ui using autossh for persistence
autossh -M 0 -f -N -L 8080:localhost:8080 a8
