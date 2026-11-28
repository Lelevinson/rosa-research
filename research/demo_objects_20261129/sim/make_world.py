"""Generate the objects world SDF (study-local). LABEL: object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only.
World frame = robot base_link frame (the robot is spawned at the world origin, base_link identity), table top at z = 0 (same height as the robot base).
Usage: python make_world.py <out.sdf> [--block X Y YAW] [--tray X Y]   (metres, radians; block at rest on the table, tray on the table)"""
import argparse
import math
from pathlib import Path

BLOCK_SIZE = 0.045            # 4.5 cm cube
TRAY = dict(floor=(0.24, 0.18, 0.01), wall=0.012, wall_h=0.03)


def block(x, y, yaw):
    s = BLOCK_SIZE
    return f"""
    <model name="red_block">
      <pose>{x} {y} {s / 2} 0 0 {yaw}</pose>
      <link name="block_link">
        <inertial><mass>0.05</mass><inertia><ixx>0.00002</ixx><iyy>0.00002</iyy><izz>0.00002</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <collision name="c"><geometry><box><size>{s} {s} {s}</size></box></geometry>
          <surface><friction><ode><mu>1.5</mu><mu2>1.5</mu2></ode></friction><contact><ode><kp>100000</kp><kd>100</kd></ode></contact></surface></collision>
        <visual name="v"><geometry><box><size>{s} {s} {s}</size></box></geometry>
          <material><ambient>0.85 0.05 0.05 1</ambient><diffuse>0.85 0.05 0.05 1</diffuse></material></visual>
      </link>
    </model>"""


def tray(x, y):
    fw, fd, fh = TRAY['floor']
    w, wh = TRAY['wall'], TRAY['wall_h']
    def box(name, px, py, pz, sx, sy, sz, color):
        return f"""
        <collision name="{name}_c"><pose>{px} {py} {pz}</pose><geometry><box><size>{sx} {sy} {sz}</size></box></geometry></collision>
        <visual name="{name}_v"><pose>{px} {py} {pz}</pose><geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
          <material><ambient>{color}</ambient><diffuse>{color}</diffuse></material></visual>"""
    color = '0.15 0.35 0.75 1'
    parts = box('floor', 0, 0, fh / 2, fw, fd, fh, color)
    parts += box('wall_n', 0, fd / 2 - w / 2, fh + wh / 2, fw, w, wh, color) + box('wall_s', 0, -fd / 2 + w / 2, fh + wh / 2, fw, w, wh, color)
    parts += box('wall_e', fw / 2 - w / 2, 0, fh + wh / 2, w, fd, wh, color) + box('wall_w', -fw / 2 + w / 2, 0, fh + wh / 2, w, fd, wh, color)
    return f"""
    <model name="tray">
      <static>true</static>
      <pose>{x} {y} 0 0 0 0</pose>
      <link name="tray_link">{parts}
      </link>
    </model>"""


def world(block_xy_yaw=(0.45, 0.10, 0.0), tray_xy=(0.45, -0.28)):
    return f"""<?xml version="1.0"?>
<!-- STUDY-LOCAL objects world. LABEL: object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only. -->
<sdf version="1.9">
  <world name="objects_world">
    <physics name="1ms" type="ignored"><max_step_size>0.002</max_step_size><real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <gravity>0 0 -9.8</gravity>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows><pose>0 0 10 0 0 0</pose><diffuse>0.9 0.9 0.9 1</diffuse><direction>-0.5 0.1 -0.9</direction></light>
    <model name="ground">
      <static>true</static>
      <link name="g"><collision name="c"><pose>0 0 -0.7 0 0 0</pose><geometry><plane><normal>0 0 1</normal><size>10 10</size></plane></geometry></collision>
        <visual name="v"><pose>0 0 -0.7 0 0 0</pose><geometry><plane><normal>0 0 1</normal><size>10 10</size></plane></geometry><material><ambient>0.75 0.75 0.75 1</ambient><diffuse>0.75 0.75 0.75 1</diffuse></material></visual></link>
    </model>
    <model name="table">
      <static>true</static>
      <pose>0.55 0 -0.35 0 0 0</pose>
      <link name="table_link">
        <collision name="c"><geometry><box><size>1.0 1.2 0.70</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>1.0 1.2 0.70</size></box></geometry><material><ambient>0.6 0.45 0.3 1</ambient><diffuse>0.6 0.45 0.3 1</diffuse></material></visual>
      </link>
    </model>{block(*block_xy_yaw)}{tray(*tray_xy)}
  </world>
</sdf>
"""


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--block', nargs=3, type=float, default=[0.45, 0.10, 0.0])
    ap.add_argument('--tray', nargs=2, type=float, default=[0.45, -0.28])
    a = ap.parse_args()
    Path(a.out).write_text(world(tuple(a.block), tuple(a.tray)), encoding='utf-8')
    print(a.out)
