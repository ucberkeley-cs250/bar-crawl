


# location of your code on scratch on the master node
master_rocket_chip_dir = "/scratch/sagark/rocket-chip"
# risc-v tools installation. should be on nscratch
rvenv = "/nscratch/sagark/celery-workspace/test-rv"
env_RISCV = rvenv
env_PATH = rvenv+"/bin:$PATH"
env_LD_LIBRARY = rvenv+"/lib"
MODEL='Top'
CONF = 'DefaultCPPConfig'


distribute_rocket_chip_loc = "/nscratch/sagark/celery-workspace/"


