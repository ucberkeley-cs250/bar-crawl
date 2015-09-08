from tasks import add

num_pass = 5000
num_fail = 500

res = []
for x in range(num_pass):
    res.append(add.delay(34))

for x in range(num_fail):
    res.append(add.delay(3))

for x in range(num_pass+num_fail):
    while not res[x].ready():
        pass


for x in range(num_pass+num_fail):
    print(res[x].get())
