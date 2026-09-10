import argparse
import sys
import time

from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args


def parse_args(args):
    parser = argparse.ArgumentParser(description='Send a bounded AR-01 velocity command.')
    parser.add_argument('--linear', type=float, default=0.3, help='Forward speed in m/s.')
    parser.add_argument('--angular', type=float, default=0.0, help='Yaw rate in rad/s.')
    parser.add_argument('--duration', type=float, default=2.0, help='Command duration in seconds.')
    return parser.parse_args(remove_ros_args(args)[1:])


def publish_command(node, publisher, linear, angular):
    message = TwistStamped()
    message.header.stamp = node.get_clock().now().to_msg()
    message.header.frame_id = 'base_footprint'
    message.twist.linear.x = linear
    message.twist.angular.z = angular
    publisher.publish(message)


def main(args=None):
    args = sys.argv if args is None else args
    options = parse_args(args)
    if options.duration <= 0.0:
        raise SystemExit('--duration must be greater than zero')

    rclpy.init(args=args)
    node = Node('ar01_cmd_test')
    publisher = node.create_publisher(TwistStamped, '/cmd_vel', 10)

    try:
        node.get_logger().info(
            f'Commanding linear={options.linear:.3f} m/s, '
            f'angular={options.angular:.3f} rad/s for {options.duration:.1f} s'
        )
        deadline = time.monotonic() + options.duration
        while rclpy.ok() and time.monotonic() < deadline:
            publish_command(node, publisher, options.linear, options.angular)
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        if rclpy.ok():
            for _ in range(3):
                publish_command(node, publisher, 0.0, 0.0)
                rclpy.spin_once(node, timeout_sec=0.05)
        node.destroy_node()
        rclpy.shutdown()
