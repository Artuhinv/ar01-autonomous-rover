import argparse
import math
import sys
import time

from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import remove_ros_args


def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def yaw_from_quaternion(quaternion):
    sin_yaw = 2.0 * (
        quaternion.w * quaternion.z + quaternion.x * quaternion.y
    )
    cos_yaw = 1.0 - 2.0 * (
        quaternion.y * quaternion.y + quaternion.z * quaternion.z
    )
    return math.atan2(sin_yaw, cos_yaw)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Run the ROS-only AR-01 P0 course: 1 m, 90 degrees, 1 m.'
    )
    parser.add_argument('--distance', type=float, default=1.0, help='Each straight leg in m.')
    parser.add_argument('--turn-degrees', type=float, default=90.0, help='Course turn angle.')
    parser.add_argument('--linear-speed', type=float, default=0.30, help='Straight speed in m/s.')
    parser.add_argument('--angular-speed', type=float, default=0.50, help='Turn speed in rad/s.')
    parser.add_argument('--cmd-topic', default='/cmd_vel')
    parser.add_argument('--odom-topic', default='/odom')
    options = parser.parse_args(remove_ros_args(args)[1:])
    if options.distance <= 0.0:
        parser.error('--distance must be greater than zero')
    if options.linear_speed <= 0.0 or options.angular_speed <= 0.0:
        parser.error('speeds must be greater than zero')
    return options


class CourseRunner(Node):
    def __init__(self, options):
        super().__init__('ar01_cmd_test')
        self.options = options
        self.pose = None
        self.publisher = self.create_publisher(TwistStamped, options.cmd_topic, 10)
        self.create_subscription(
            Odometry,
            options.odom_topic,
            self.odom_callback,
            qos_profile_sensor_data,
        )

    def odom_callback(self, message):
        position = message.pose.pose.position
        self.pose = (
            position.x,
            position.y,
            yaw_from_quaternion(message.pose.pose.orientation),
        )

    def publish_velocity(self, linear=0.0, angular=0.0):
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'base_footprint'
        message.twist.linear.x = linear
        message.twist.angular.z = angular
        self.publisher.publish(message)

    def wait_for_odometry(self, timeout=15.0):
        deadline = time.monotonic() + timeout
        while rclpy.ok() and self.pose is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.pose is None:
            raise RuntimeError(f'No odometry received on {self.options.odom_topic}')

    def stop(self, duration=0.6):
        deadline = time.monotonic() + duration
        while rclpy.ok() and time.monotonic() < deadline:
            self.publish_velocity()
            rclpy.spin_once(self, timeout_sec=0.05)

    def drive(self, distance):
        start_x, start_y, _ = self.pose
        timeout = distance / self.options.linear_speed * 3.0 + 5.0
        deadline = time.monotonic() + timeout
        self.get_logger().info(f'DRIVE {distance:.2f} m')

        while rclpy.ok() and time.monotonic() < deadline:
            x, y, _ = self.pose
            travelled = math.hypot(x - start_x, y - start_y)
            if travelled >= distance:
                self.stop()
                self.get_logger().info(f'DRIVE complete: {travelled:.3f} m')
                return
            self.publish_velocity(linear=self.options.linear_speed)
            rclpy.spin_once(self, timeout_sec=0.05)
        raise RuntimeError('Straight segment timed out')

    def turn(self, angle):
        start_yaw = self.pose[2]
        timeout = abs(angle) / self.options.angular_speed * 3.0 + 5.0
        deadline = time.monotonic() + timeout
        direction = 1.0 if angle >= 0.0 else -1.0
        self.get_logger().info(f'TURN {math.degrees(angle):.1f} deg')

        while rclpy.ok() and time.monotonic() < deadline:
            turned = normalize_angle(self.pose[2] - start_yaw)
            if abs(turned) >= abs(angle):
                self.stop()
                self.get_logger().info(
                    f'TURN complete: {math.degrees(turned):.1f} deg'
                )
                return
            self.publish_velocity(angular=direction * self.options.angular_speed)
            rclpy.spin_once(self, timeout_sec=0.05)
        raise RuntimeError('Turn segment timed out')


def main(args=None):
    args = sys.argv if args is None else args
    options = parse_args(args)
    rclpy.init(args=args)
    node = CourseRunner(options)
    exit_code = 0

    try:
        node.get_logger().info('STOP')
        node.stop()
        node.wait_for_odometry()
        node.drive(options.distance)
        node.turn(math.radians(options.turn_degrees))
        node.drive(options.distance)
        node.get_logger().info('STOP — P0 course complete')
    except (KeyboardInterrupt, RuntimeError) as error:
        node.get_logger().error(str(error))
        exit_code = 1
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()

    raise SystemExit(exit_code)
