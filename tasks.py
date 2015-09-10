
from celery import Celery
from paths import *
from fabric.api import *
from fabric.tasks import execute

#app = Celery('tasks', backend='rpc://', broker='amqp://localhost')
app = Celery('tasks', backend='rpc://', broker='redis://a8.millennium.berkeley.edu:6379')


#def actually_do_stuff(n):
#    if n == 0: 
#        return 0
#    if n == 1:
#        return 1
#    return actually_do_stuff(n-1) + actually_do_stuff(n-2)


#@app.task(bind=True)
#def add(self, x):
#    print "HELLO FROM THIS TASK"
#    print "I AM: " + str(self.request.id)
#    q = """ alsidhfliahsdlfiahsdlfihasdlfihasdf asdf asd fa sdf asd fasd fa sdf asd fasd f
#asdf asd fasdfasdfas dfasdfk asdfk asjdlfka jsdlkfj aslkdf jalskdjf laksdj flkasdj flkasj dfa
#sj dfa s
#dfja;skdjfklasd dfjlkas djflk
#aj sdlf
#ajsd
#fa
#sdf
#asd
#fasdfjaslkdfjaaaaaslkdjflkajsdlkfjalskdfjlkasdjfklajsdlkfjasdlkfjalksdfjlaksdjflkasdjflaskjdfklasdjf
#asdflkajsldfjalksdjflaksdjflkasjdflkasjdflkajsdlkfjasdlkfjasldkfjaslkdfjalksdfjlaksdjfklasdjflkasdjfklasdjf
#afkjasdlkfjaslkdfjlaksdjflkasdjflkasdjflkasjd fas df asdf asd fa sdf asd fa sdf asd fa sdf asd fa sdf """
#
#    if x == 3:
#        raise Exception("TEST EXCEPTION")
#    return q + str(actually_do_stuff(x))

sample = "./emulator-Top-DefaultCPPConfig +dramsim +max-cycles=100000000 +verbose +loadmem=../riscv-tests/isa/{}.hex none 3>&1 1>&2 2>&3 | /nscratch/sagark/celery-workspace/test-rv/bin/spike-dasm  > ../../{}.out && [ $PIPESTATUS -eq 0 ]"

testname = "rv64ui-v-ori"





def test1(test_to_run):
    """ run a test """
    # todo: looks like we can't run this from any other directory, dramsim
    # path is hardcoded?
    with lcd(distribute_rocket_chip_loc + '/distribute/cpptest/emulator'), shell_env(RISCV=env_RISCV, PATH=env_PATH, LD_LIBRARY_PATH=env_LD_LIBRARY), settings(warn_only=True):
        res = local(sample.format(test_to_run, test_to_run), shell='/bin/bash')
        if res.failed:
            return "FAIL"
        return "PASS"



@app.task(bind=True)
def cpptest(self, testname):
    return execute(test1, testname)

