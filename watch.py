import redis
from crawlutils import *
import sys
from userconfig import UserJobConfig
import os

# if user has specified a config file, use that, else default.conf
if len(sys.argv) > 1:
    userjobconfig = UserJobConfig(sys.argv[1])
else:
    userjobconfig = UserJobConfig()

def get_list_of_jobs():
    j = os.listdir(userjobconfig.distribute_rocket_chip_loc)
    j.sort(reverse=True)
    j = j[:10]
    return j

msg = """The following jobs were run recently. Select the correct one to monitor:"""

print msg

j = get_list_of_jobs()
for x in range(len(j)):
    print("[" + str(x) + "] " + j[x])

jnum = int(input(''))

msg2 = """The following designs were detected.

If the list below is not what you expect, please make sure the jackhammer run 
has completed first. 

Please select a design number to watch:"""

print(msg2)

def get_design_names(fname):
    des = []
    a = open(fname, 'r')
    b = a.readlines()
    a.close()

    for x in b:
        linesplit = x.split(' ')
        if linesplit[0] == 'class':
            des.append(linesplit[1])
    return des

designs_scala = userjobconfig.distribute_rocket_chip_loc + '/' + j[jnum] + '/' + userjobconfig.CONF + '.scala'
designs = get_design_names(designs_scala)

for x in range(len(designs)):
    print("[" + str(x) + "] " + designs[x])

d = int(input(''))


design_name = j[jnum] + "-" + designs[d]

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
