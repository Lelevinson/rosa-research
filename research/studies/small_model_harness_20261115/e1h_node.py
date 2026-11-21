"""E1h fixture node (stock rclpy + std_msgs only). Usage: e1h_node.py <graph.json> <node key>. Unlike the Stage 3 node, each node has its own namespace."""
import json
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Int32, String

MSG = {"std_msgs/msg/String": (String, lambda: String(data="tick")), "std_msgs/msg/Int32": (Int32, lambda: Int32(data=1)),
       "std_msgs/msg/Float32": (Float32, lambda: Float32(data=1.0))}


def main():
    graph = json.load(open(sys.argv[1]))
    spec = next(n for n in graph["nodes"] if n["key"] == sys.argv[2])
    rclpy.init()
    node = Node(spec["name"], namespace=spec["namespace"])
    for name, value in spec["params"].items():
        node.declare_parameter(name, value)
    pubs = []
    for t in spec["pubs"]:
        cls, make = MSG[t["type"]]
        pubs.append((node.create_publisher(cls, t["name"], 10), make))
    for t in spec["subs"]:
        node.create_subscription(MSG[t["type"]][0], t["name"], lambda msg: None, 10)
    node.create_timer(1.0, lambda: [p.publish(m()) for p, m in pubs])
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
