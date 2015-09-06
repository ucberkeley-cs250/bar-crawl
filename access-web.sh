#!/bin/sh

# port forward to access the web ui
# localhost is from the server's perspective, in this case a8 (a8.millennium.berkeley.edu)
ssh -L 8080:localhost:8080 a8
