import os
import string

""" USER CONFIG. Need to wrap this up and send to subtasks """
class UserJobConfig:

    def __init__(self):
        # your username
        # bar-crawl will use /scratch/USERNAME/celery-temp for compiles
        self.username = 'sagark'

        # enable/disable redis stdout/stderr logging
        self.logging_on = False

        # your rocket-chip work directory on the master node
        # bar-crawl will look at commit hashes here to make sure it's testing the
        # right code with the right toolchain/tests
        self.master_rocket_chip_dir = "/scratch/sagark/launch-vlsi-new-shaped/rocket-chip"
        # risc-v tools installation. should be on nscratch
        #
        # it is expected that you name this directory after the commit ID 
        # of riscv-tools that you installed it from e.g:
        #
        # /nscratch/bar-crawl/tools-installs/0129c14c9837ef925e7b1d9513e32a5ffcaea75f
        # 
        # To "atomically" install new tools when there is the potential for 
        # multiple people to be running jobs, you should first install the tools
        # into a staging directory and then move them into the right directory.
        #
        # When you launch a job, bar-crawl will check this directory name against
        # the commit hash  of riscv-tools submodule in your working directory 
        # and prevent you from proceeding if there is a mismatch
        #
        # TODO: can auto-detect this based on what it's supposed to be from 
        # looking at master_rocket_chip_dir
        self.rvenv = "/nscratch/bar-crawl/tools-installs/21eb7c03e53504b13fdc3c0c547e07a48c457419"

        """ DO NOT MODIFY """
        self.env_RISCV = self.rvenv
        self.env_PATH = self.rvenv+"/bin:$PATH"
        self.env_LD_LIBRARY = self.rvenv+"/lib"
        self.rvenv_installed_hash = self.rvenv.split("/")[-1]
        """ END DO NOT MODIFY """

        self.MODEL='Top' # this currently should not be changed. see README
        self.CONF = 'EOS24Config' # this is the overall config name (as opposed to EOS24Config0, EOS24Config1, etc)

        """ DO NOT MODIFY """
        self.shell_env_args = {
                'RISCV': self.env_RISCV,
                'PATH': self.env_PATH,
                'LD_LIBRARY_PATH': self.env_LD_LIBRARY,
                'CONFIG': self.CONF
        }
        """ END DO NOT MODIFY """

        # the next two locations are the github repository url of your 
        # copy of rocket-chip and the tests you intend to run
        self.rocket_chip_location = 'git@github.com:sagark/rocket-chip'
        self.tests_location = 'git@github.com:ucb-bar/esp-tests.git'

        # If you want, you can set a tag here to make your output directory
        # easier to identify. this tag will be tacked onto the end of the job
        # output directory name. It can only contain letters, numbers, and
        # dashes. This is especially useful if you have uncommitted changes.
        self.human_tag = "-sagar-no-logging-new-fp1"

        """ DO NOT MODIFY """
        for x in self.human_tag:
            if x not in string.ascii_letters + string.digits + "-":
                print "ERROR, character is not allowed in human_tag: " + x
                exit(0)
        """ END DO NOT MODIFY """

        # This should be set on a per-project basis, so that users
        # trying out a design for a particular project will all make job
        # directories in one directory in one shared dir
        self.distribute_rocket_chip_loc = "/nscratch/bar-crawl/hwacha"

        # set of "tests" to run
        # remove/comment out items that you don't wish to run
        #
        # TODO: rename this
        self.tests = [
                'emulator', 
                'vsim', 
                'vcs-sim-rtl', 
                'dc-syn',
                'vcs-sim-gl-syn',
                'icc-par',
        ]

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

        self.hashes = {} # populated later

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        asdict = self.__dict__
        keys = filter(lambda x: x != 'mailgun_api', asdict.keys())
        p = { k: asdict[k] for k in keys }
        return str(p)
