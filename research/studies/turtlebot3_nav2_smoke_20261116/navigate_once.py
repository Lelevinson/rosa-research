#!/usr/bin/env python3
"""Initialize AMCL at the actual default Gazebo spawn and send one bounded goal."""
import math
import time
import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.action import ActionClient
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

SPAWN=(-2.0,-0.5)  # installed turtlebot3_world.launch.py defaults
GOAL=(-1.5,-0.5)
NODES=('map_server','amcl','controller_server','planner_server','bt_navigator',
       'smoother_server','behavior_server','waypoint_follower','velocity_smoother',
       'route_server','collision_monitor','docking_server')

def spin_until(node, predicate, seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        rclpy.spin_once(node,timeout_sec=.2)
        if predicate(): return True
    return False

def main():
    rclpy.init(); node=rclpy.create_node('rosa_nav2_single_goal_check'); data={}
    mapq=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(OccupancyGrid,'/map',lambda m:data.update(map=m),mapq)
    node.create_subscription(Odometry,'/odom',lambda m:data.update(odom=m),10)
    node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',lambda m:data.update(amcl=m),10)
    pub=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
    clients={name:node.create_client(GetState,f'/{name}/get_state') for name in NODES}
    try:
        if not spin_until(node,lambda:'map' in data and 'odom' in data and clients['amcl'].service_is_ready(),45): raise RuntimeError('map, odometry, or AMCL service unavailable')
        grid=data['map']; ox=grid.info.origin.position.x; oy=grid.info.origin.position.y; res=grid.info.resolution
        def cell(x,y):
            cx=int((x-ox)/res); cy=int((y-oy)/res)
            if not(0<=cx<grid.info.width and 0<=cy<grid.info.height): return None
            return grid.data[cy*grid.info.width+cx]
        samples=[(round(SPAWN[0]+(GOAL[0]-SPAWN[0])*i/10,3),round(SPAWN[1]+(GOAL[1]-SPAWN[1])*i/10,3),cell(SPAWN[0]+(GOAL[0]-SPAWN[0])*i/10,SPAWN[1]+(GOAL[1]-SPAWN[1])*i/10)) for i in range(11)]
        print('map frame, size, origin, resolution',grid.header.frame_id,grid.info.width,grid.info.height,ox,oy,res,flush=True)
        print('spawn-to-goal map centerline samples',samples,flush=True)
        if any(v is None or v < 0 or v >= 65 for _,_,v in samples): raise RuntimeError('spawn-to-goal map centerline is unknown or occupied')
        pose=PoseWithCovarianceStamped();pose.header.frame_id='map';pose.pose.pose.position.x=SPAWN[0];pose.pose.pose.position.y=SPAWN[1];pose.pose.pose.orientation.w=1.0
        pose.pose.covariance[0]=0.01;pose.pose.covariance[7]=0.01;pose.pose.covariance[35]=0.01
        for _ in range(3):
            pose.header.stamp=node.get_clock().now().to_msg();pub.publish(pose);spin_until(node,lambda:'amcl' in data,2)
        if 'amcl' not in data: raise RuntimeError('AMCL pose not received after initial pose')
        amcl=data['amcl'].pose.pose.position;print('AMCL pose after initialization',round(amcl.x,3),round(amcl.y,3),flush=True)
        until=time.monotonic()+70; states={}
        while time.monotonic()<until:
            for name,c in clients.items():
                if c.service_is_ready():
                    f=c.call_async(GetState.Request());spin_until(node,f.done,1)
                    if f.done() and f.result():states[name]=f.result().current_state.label
            if all(states.get(n)=='active' for n in NODES):break
            rclpy.spin_once(node,timeout_sec=.2)
        print('lifecycle states',states,flush=True)
        if not all(states.get(n)=='active' for n in NODES): raise RuntimeError('not all required Nav2 lifecycle nodes became active')
        action=ActionClient(node,NavigateToPose,'/navigate_to_pose')
        if not action.wait_for_server(timeout_sec=10): raise RuntimeError('NavigateToPose server unavailable')
        goal=NavigateToPose.Goal();goal.pose.header.frame_id='map';goal.pose.header.stamp=node.get_clock().now().to_msg();goal.pose.pose.position.x=GOAL[0];goal.pose.pose.position.y=GOAL[1];goal.pose.pose.orientation.w=1.0
        sent=action.send_goal_async(goal)
        if not spin_until(node,sent.done,10) or not sent.result().accepted:raise RuntimeError('navigation goal not accepted')
        handle=sent.result(); future=handle.get_result_async()
        if not spin_until(node,future.done,90):
            cancel=handle.cancel_goal_async();spin_until(node,cancel.done,5);raise RuntimeError('navigation goal timeout; cancellation requested')
        result=future.result(); print('goal result status',result.status,'(4 means succeeded)',flush=True)
        odom=data['odom'].pose.pose.position;print('last odometry',round(odom.x,3),round(odom.y,3),flush=True)
        if result.status!=GoalStatus.STATUS_SUCCEEDED:raise RuntimeError('navigation goal did not succeed')
        print('NAVIGATION PASS',flush=True)
    finally:
        node.destroy_node();rclpy.shutdown()

if __name__=='__main__': main()
