from celery import Celery

#app = Celery('tasks', backend='rpc://', broker='amqp://localhost')
app = Celery('tasks', backend='rpc://', broker='redis://a8.millennium.berkeley.edu:6379')


def actually_do_stuff(n):
    if n == 0: 
        return 0
    if n == 1:
        return 1
    return actually_do_stuff(n-1) + actually_do_stuff(n-2)


@app.task(bind=True)
def add(self, x):
    print "HELLO FROM THIS TASK"
    print "I AM: " + str(self.request.id)
    q = """ alsidhfliahsdlfiahsdlfihasdlfihasdf asdf asd fa sdf asd fasd fa sdf asd fasd f
asdf asd fasdfasdfas dfasdfk asdfk asjdlfka jsdlkfj aslkdf jalskdjf laksdj flkasdj flkasj dfa
sj dfa s
dfja;skdjfklasd dfjlkas djflk
aj sdlf
ajsd
fa
sdf
asd
fasdfjaslkdfjaaaaaslkdjflkajsdlkfjalskdfjlkasdjfklajsdlkfjasdlkfjalksdfjlaksdjflkasdjflaskjdfklasdjf
asdflkajsldfjalksdjflaksdjflkasjdflkasjdflkajsdlkfjasdlkfjasldkfjaslkdfjalksdfjlaksdjfklasdjflkasdjfklasdjf
afkjasdlkfjaslkdfjlaksdjflkasdjflkasdjflkasjd fas df asdf asd fa sdf asd fa sdf asd fa sdf asd fa sdf """

    if x == 3:
        raise Exception("TEST EXCEPTION")
    return q + str(actually_do_stuff(x))






#def copy_scratch_nscratch():



