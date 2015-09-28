bar-crawl: Berkeley Architecture Research Cluster for Running Asic WorkLoads
==============================================================================

Prereqs:
-----------------------
- TODO: Install celery, fabric or just add mine to PYTHONPATH
- Use ssh forwarding


How to use:
-----------------------

1. Choose a "master" node and login. On that node, create a directory:

```
/scratch/YOUR_USERNAME/hwacha-celery
```

Inside it, clone rocket-chip. This will be your working directory. Celery will take the latest commit in this repo and use it to run your distributed tests. For now, Celery pulls from GitHub, so you'll need to make sure that your commit is pushed publicly.

2. Next, you need to start workers on the cluster. Eventually, the workers will be left running. For now, they need to be manually started since they need to be restarted anyway whenever changes are made to bar-crawl. To start the workers:
  [Inside bar-crawl]
  ./run-fabric.sh



