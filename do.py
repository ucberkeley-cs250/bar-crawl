from tasks import add

result = add.delay(35)


res = []
for x in range(35):
    if x < 10:
	res.append(add.delay(3))
    res.append(add.delay(33))


for x in range(45):
    while not res[x].ready():
        pass


for x in range(45):
    print(res[x].get())
