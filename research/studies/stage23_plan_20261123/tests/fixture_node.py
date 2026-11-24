"""A named fixture node that publishes /settle_test (stands in for a turtlesim/Nav2 node)."""
import rclpy
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node("fixture_publisher")
publisher = node.create_publisher(String, "/settle_test", 10)
node.create_timer(0.5, lambda: publisher.publish(String(data="x")))
rclpy.spin(node)
