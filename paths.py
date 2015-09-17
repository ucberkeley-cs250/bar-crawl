""" Directory structure:


in /nscratch/sagark/celery-workspace:


distribute/
    -Designs.scala
    -Design0
    -Design1
    -Design2
        -emulator (C++)
        -vsim
        -etc


-------------- 
exec flow:

    1) Master on /scratch/sagark/hwacha-celery/rocket-chip
        a) runs jackhammer to generate rocket-chip/src/main/scala/configs/Designs.scala
        b) Copy Designs.scala to /nscratch/sagark/celery-workspace/distribute/
        c) Run distributed compile jobs for each design
            Arg to each compile task is just design name (like Design0)

            1) mkdir /scratch/sagark/celery-temp/design-name && cd there
            2) git clone git@github.com:sagark/rocket-chip
            3) cd rocketchip && git submodule update --init
            4) copy Designs.scala from /nscratch/sagark/celery-workspace/distribute/
                to src/main/scala/configs/
            5) Run compile jobs for emulator, vsim, etc
                Copy to 
                /nscratch/sagark/celery-workspace/distribute/DesignN/[test type]
            6) Start subtasks to run tests

"""


# location of your code on scratch on the master node
master_rocket_chip_dir = "/scratch/sagark/hwacha-celery/rocket-chip"

# risc-v tools installation. should be on nscratch
rvenv = "/nscratch/sagark/celery-workspace/test-rv"
env_RISCV = rvenv
env_PATH = rvenv+"/bin:$PATH"
env_LD_LIBRARY = rvenv+"/lib"



MODEL='Top'
CONF = 'HwachaVLSIConfig'


distribute_rocket_chip_loc = "/nscratch/sagark/celery-workspace/distribute"

shell_env_args = {
        'RISCV': env_RISCV,
        'PATH': env_PATH,
        'LD_LIBRARY_PATH': env_LD_LIBRARY
}

tests = ['emulator', 'vsim']
