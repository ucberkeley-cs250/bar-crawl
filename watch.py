import redis
from paths import *


design_name = 'HwachaVLSIConfig0'

red = redis.StrictRedis(**redis_conf)
ps = red.pubsub()

sofar = red.lrange(design_name, 0, -1)
sofar.reverse()
ps.subscribe(design_name)

for x in sofar:
    print x

while True:
    for item in ps.listen():
        print item['data']
