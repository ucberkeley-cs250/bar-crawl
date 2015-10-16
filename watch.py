import redis
from crawlutils import *
import sys
from userconfig import UserJobConfig

userjobconfig = UserJobConfig()

jobid = "2015-10-16-14-02-42-386a0c72-sagar-new-shape-script"
jobid2 = "2015-10-16-14-10-26-386a0c72-sagar-new-shape-script-2"

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

designs_scala = userjobconfig.master_rocket_chip_dir + '/src/main/scala/config/' + userjobconfig.CONF + '.scala'
designs = get_design_names(designs_scala)

for x in range(len(designs)):
    print("[" + str(x) + "] " + designs[x])

d = int(input(''))


design_name = jobid2 + "-" + designs[d]

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
