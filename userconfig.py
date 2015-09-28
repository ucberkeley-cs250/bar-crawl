""" USER CONFIG. Need to wrap this up and send to subtasks """
# location of your code on scratch on the master node
# -celery will run based on the latest commit here
# -make sure you've pushed to github
#
class UserJobConfig:

    # your username
    # bar-crawl will use /scratch/USERNAME/celery-temp for compiles
    username = 'sagark'

    master_rocket_chip_dir = "/scratch/sagark/hwacha-celery/rocket-chip"

    # risc-v tools installation. should be on nscratch
    rvenv = "/nscratch/sagark/celery-workspace/hwacha-rv"
    env_RISCV = rvenv
    env_PATH = rvenv+"/bin:$PATH"
    env_LD_LIBRARY = rvenv+"/lib"

    MODEL='Top'
    CONF = 'EOS24Config' # this is the overall config name (as opposed to EOS24Config0, EOS24Config1, etc)

    shell_env_args = {
            'RISCV': env_RISCV,
            'PATH': env_PATH,
            'LD_LIBRARY_PATH': env_LD_LIBRARY,
            'CONFIG': CONF
    }

    rocket_chip_location = 'git@github.com:sagark/rocket-chip'
    tests_location = 'git@github.com:ucb-bar/esp-tests.git'

    # this should probably be set on a per-project basis
    distribute_rocket_chip_loc = "/nscratch/sagark/celery-workspace/distribute"

    # set of tests to run
    # remove/comment out items that you don't wish to run
    # NOTE: emulator is non-optional. see note in tasks.py
    tests = [
            'emulator', 
            'vsim', 
            'vcs-sim-rtl', 
            'dc-syn',
    ]

