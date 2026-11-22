import os, sys, time
os.environ.update(ROS_DOMAIN_ID='232', ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST')
sys.path.insert(0, '/mnt/c/Proj/robotics/introtorobotics/rosa-research/src')
from rosa_reliability.gazebo_demo import GazeboDemo
d = GazeboDemo(sys.argv[1])
try:
    d.start(); print('ready', flush=True); time.sleep(float(sys.argv[2]))
finally:
    print(d.close())
