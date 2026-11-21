"""Disposable graph fixture, with no robot hardware or custom semantic services."""
import signal
import rclpy
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String

def main():
    rclpy.init()
    executor = SingleThreadedExecutor()
    nodes = [rclpy.create_node(f'n{i}', namespace='/nr11') for i in range(4)]
    publishers = [node.create_publisher(String, f'/nr11/t{i}', 10) for i,node in enumerate(nodes)]
    for node in nodes:
        executor.add_node(node)
    def terminate(*_):
        # shutdown() inside the spin thread's signal handler can wait on itself.
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    print('FIXTURE_READY', flush=True)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown(timeout_sec=1)
        for node in nodes:
            node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
