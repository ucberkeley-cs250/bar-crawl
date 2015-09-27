import redis
from paths import *
import sys

design_name = 'EOS24Config0'

red = redis.StrictRedis(**redis_conf)
ps = red.pubsub()

sofar = red.lrange(design_name, 0, -1)
sofar.reverse()
ps.subscribe(design_name)

for x in sofar:
    sys.stdout.write(x)

while True:
    for item in ps.listen():
        sys.stdout.write(str(item['data']))
