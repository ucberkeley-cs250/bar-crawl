import os
import string

""" USER CONFIG. Need to wrap this up and send to subtasks """
class UserJobConfig:

    def __init__(self):
        # your username
        # bar-crawl will use /scratch/USERNAME/celery-temp for compiles
        self.username = 'sagark'

        # your rocket-chip work directory on the master node
        # bar-crawl will look at commit hashes here to make sure it's testing the
        # right code with the right toolchain/tests
        self.master_rocket_chip_dir = "/scratch/sagark/hwacha-celery/rocket-chip"

        # risc-v tools installation. should be on nscratch
        # TODO: configure based on changes
        self.rvenv = "/nscratch/sagark/celery-workspace/hwacha-rv"
        self.env_RISCV = self.rvenv
        self.env_PATH = self.rvenv+"/bin:$PATH"
        self.env_LD_LIBRARY = self.rvenv+"/lib"

        self.MODEL='Top'
        self.CONF = 'EOS24Config' # this is the overall config name (as opposed to EOS24Config0, EOS24Config1, etc)

        self.shell_env_args = {
                'RISCV': self.env_RISCV,
                'PATH': self.env_PATH,
                'LD_LIBRARY_PATH': self.env_LD_LIBRARY,
                'CONFIG': self.CONF
        }

        self.rocket_chip_location = 'git@github.com:ucb-bar/rocket-chip'
        self.tests_location = 'git@github.com:ucb-bar/esp-tests.git'

        # if you want, you can set a tag here to make your output directory
        # easier to identify. this tag will be tacked onto the end of the job
        # output directory name. It can only contain letters, numbers, and
        # dashes
        #
        # this is especially useful if you have uncommitted changes
        self.human_tag = "-test"
        for x in self.human_tag:
            if x not in string.ascii_letters + string.digits + "-":
                print "ERROR, character is not allowed in human_tag: " + x
                exit(0)


        # TODO: this should probably be set on a per-project basis, so that users
        # trying out a design will all dump things into one shared dir
        self.distribute_rocket_chip_loc = "/nscratch/bar-crawl/hwacha"

        # set of tests to run
        # remove/comment out items that you don't wish to run
        # NOTE: emulator is non-optional. see note in tasks.py
        self.tests = [
                'emulator', 
                'vsim', 
                'vcs-sim-rtl', 
#                'dc-syn',
        ]

        # reads out the list of tests to run from the testnames file
        tfile = open('testnames', 'r')
        self.runtests = map(lambda x: x.strip(), tfile.readlines())
        tfile.close()

        self.enableEMAIL = True
        # you need to obtain a mailgun API key for emails
        if (self.enableEMAIL):
            """ Get the mailgun@bar-crawl.sagark.org API key.
            Change this if you don't have access to /nscratch"""
            apifile = open('/nscratch/bar-crawl/mailgun-api', 'r')
            self.mailgun_api = apifile.readlines()[0].strip()
            apifile.close()
            self.email_addr = "sagark@eecs.berkeley.edu"
            self.cc_addr = "karandikarsagar@gmail.com"


    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        asdict = self.__dict__
        keys = filter(lambda x: x != 'runtests', asdict.keys())
        p = { k: asdict[k] for k in keys }
        #st = """Using Master at: {}
        #Using $RISCV at: {}""".format(self.master_rocket_chip_dir, self.rvenv)
        return str(p)
