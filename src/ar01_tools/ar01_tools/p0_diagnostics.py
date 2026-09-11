import argparse
import math
import sys
import time

from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import remove_ros_args
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu, JointState, LaserScan
from std_msgs.msg import String


def finite(*values):
    return all(math.isfinite(value) for value in values)


def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def quaternion_rpy(quaternion):
    sin_roll = 2.0 * (
        quaternion.w * quaternion.x + quaternion.y * quaternion.z
    )
    cos_roll = 1.0 - 2.0 * (
        quaternion.x * quaternion.x + quaternion.y * quaternion.y
    )
    roll = math.atan2(sin_roll, cos_roll)

    sin_pitch = 2.0 * (
        quaternion.w * quaternion.y - quaternion.z * quaternion.x
    )
    pitch = math.asin(max(-1.0, min(1.0, sin_pitch)))

    sin_yaw = 2.0 * (
        quaternion.w * quaternion.z + quaternion.x * quaternion.y
    )
    cos_yaw = 1.0 - 2.0 * (
        quaternion.y * quaternion.y + quaternion.z * quaternion.z
    )
    yaw = math.atan2(sin_yaw, cos_yaw)
    return roll, pitch, yaw


def parse_args(args):
    parser = argparse.ArgumentParser(description='Run the AR-01 P0 ROS acceptance test.')
    parser.add_argument('--timeout', type=float, default=25.0)
    parser.add_argument('--forward-seconds', type=float, default=1.5)
    parser.add_argument('--rotation-seconds', type=float, default=1.5)
    return parser.parse_args(remove_ros_args(args)[1:])


class P0Diagnostics(Node):
    def __init__(self):
        super().__init__('ar01_p0_diagnostics')
        self.latest = {}
        self.max_abs_imu_z = 0.0
        self.results = []

        description_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            String,
            '/robot_description',
            lambda message: self.remember('robot_description', message),
            description_qos,
        )
        self.create_subscription(
            Clock,
            '/clock',
            lambda message: self.remember('clock', message),
            qos_profile_sensor_data,
        )
        self.create_subscription(
            JointState,
            '/joint_states',
            lambda message: self.remember('joint_states', message),
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Odometry,
            '/odom',
            lambda message: self.remember('odom', message),
            qos_profile_sensor_data,
        )
        self.create_subscription(
            LaserScan,
            '/scan',
            lambda message: self.remember('scan', message),
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Imu,
            '/imu/data',
            self.imu_callback,
            qos_profile_sensor_data,
        )
        self.command_publisher = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.controllers_client = self.create_client(
            ListControllers,
            '/controller_manager/list_controllers',
        )

    def remember(self, key, message):
        self.latest[key] = message

    def imu_callback(self, message):
        self.latest['imu'] = message
        self.max_abs_imu_z = max(
            self.max_abs_imu_z,
            abs(message.angular_velocity.z),
        )

    def add_result(self, label, passed, detail=''):
        self.results.append((label, bool(passed), detail))

    def wait_for_messages(self, timeout):
        required = {'robot_description', 'clock', 'joint_states', 'odom', 'scan', 'imu'}
        deadline = time.monotonic() + timeout
        while rclpy.ok() and not required.issubset(self.latest) and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

    def check_controllers(self, timeout):
        if not self.controllers_client.wait_for_service(timeout_sec=timeout):
            return False, 'controller_manager service unavailable'
        future = self.controllers_client.call_async(ListControllers.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        if not future.done() or future.result() is None:
            return False, 'controller list timed out'
        states = {controller.name: controller.state for controller in future.result().controller}
        expected = {'joint_state_broadcaster', 'diff_drive_controller'}
        passed = expected.issubset(states) and all(states[name] == 'active' for name in expected)
        return passed, str(states)

    def publish_velocity(self, linear=0.0, angular=0.0):
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'base_footprint'
        message.twist.linear.x = linear
        message.twist.angular.z = angular
        self.command_publisher.publish(message)

    def command_for(self, duration, linear=0.0, angular=0.0):
        deadline = time.monotonic() + duration
        while rclpy.ok() and time.monotonic() < deadline:
            self.publish_velocity(linear, angular)
            rclpy.spin_once(self, timeout_sec=0.05)

    def stop(self, duration=0.8):
        self.command_for(duration)

    def odom_pose(self):
        pose = self.latest['odom'].pose.pose
        _, _, yaw = quaternion_rpy(pose.orientation)
        return pose.position.x, pose.position.y, yaw

    def front_range(self):
        scan = self.latest['scan']
        index = round((0.0 - scan.angle_min) / scan.angle_increment)
        values = scan.ranges[max(0, index - 2):index + 3]
        usable = [value for value in values if math.isfinite(value)]
        return sum(usable) / len(usable) if usable else math.inf

    def run(self, options):
        self.wait_for_messages(options.timeout)

        description = self.latest.get('robot_description')
        self.add_result(
            'robot_description',
            description is not None and '<robot' in description.data,
        )

        controllers_ok, controllers_detail = self.check_controllers(options.timeout)
        self.add_result('controllers', controllers_ok, controllers_detail)

        clock = self.latest.get('clock')
        self.add_result(
            '/clock',
            clock is not None and (clock.clock.sec > 0 or clock.clock.nanosec > 0),
        )

        joints = self.latest.get('joint_states')
        joints_ok = (
            joints is not None
            and {'left_wheel_joint', 'right_wheel_joint'}.issubset(joints.name)
            and all(math.isfinite(value) for value in joints.position)
        )
        self.add_result('/joint_states', joints_ok)

        odom = self.latest.get('odom')
        odom_values = [] if odom is None else [
            odom.pose.pose.position.x,
            odom.pose.pose.position.y,
            odom.pose.pose.orientation.x,
            odom.pose.pose.orientation.y,
            odom.pose.pose.orientation.z,
            odom.pose.pose.orientation.w,
        ]
        self.add_result('/odom', bool(odom_values) and finite(*odom_values))

        scan = self.latest.get('scan')
        scan_ok = (
            scan is not None
            and len(scan.ranges) == 720
            and scan.header.frame_id == 'lidar_link'
            and not any(math.isnan(value) for value in scan.ranges)
        )
        self.add_result('/scan', scan_ok, '' if scan is None else f'{len(scan.ranges)} ranges')

        imu = self.latest.get('imu')
        imu_values = [] if imu is None else [
            imu.orientation.x,
            imu.orientation.y,
            imu.orientation.z,
            imu.orientation.w,
            imu.angular_velocity.x,
            imu.angular_velocity.y,
            imu.angular_velocity.z,
            imu.linear_acceleration.x,
            imu.linear_acceleration.y,
            imu.linear_acceleration.z,
        ]
        imu_ok = (
            imu is not None
            and imu.header.frame_id == 'imu_link'
            and finite(*imu_values)
        )
        self.add_result('/imu/data', imu_ok)

        prerequisites = controllers_ok and odom is not None and scan is not None and imu is not None
        if not prerequisites:
            self.add_result('forward motion', False, 'prerequisite failed')
            self.add_result('rotation', False, 'prerequisite failed')
            return

        self.stop()
        start_x, start_y, _ = self.odom_pose()
        start_front_range = self.front_range()
        self.command_for(options.forward_seconds, linear=0.25)
        self.stop()
        end_x, end_y, _ = self.odom_pose()
        end_front_range = self.front_range()
        displacement = math.hypot(end_x - start_x, end_y - start_y)
        scan_reacted = (
            math.isfinite(start_front_range)
            and math.isfinite(end_front_range)
            and end_front_range < start_front_range - 0.05
        )
        self.add_result(
            'forward motion',
            displacement > 0.15 and end_x > start_x + 0.10 and scan_reacted,
            f'd={displacement:.3f} m, front scan {start_front_range:.2f}->{end_front_range:.2f} m',
        )

        start_yaw = self.odom_pose()[2]
        self.max_abs_imu_z = 0.0
        self.command_for(options.rotation_seconds, angular=0.50)
        peak_angular_z = self.max_abs_imu_z
        self.stop()
        end_yaw = self.odom_pose()[2]
        yaw_change = abs(normalize_angle(end_yaw - start_yaw))
        roll, pitch, _ = quaternion_rpy(self.latest['imu'].orientation)
        stable = abs(roll) < 0.10 and abs(pitch) < 0.10
        self.add_result(
            'rotation',
            yaw_change > 0.25 and peak_angular_z > 0.20 and stable,
            f'yaw={math.degrees(yaw_change):.1f} deg, imu_z={peak_angular_z:.3f}, stable={stable}',
        )

    def print_report(self):
        print('\nAR-01 P0 ACCEPTANCE\n')
        for label, passed, detail in self.results:
            suffix = f' — {detail}' if detail else ''
            print(f'[{"PASS" if passed else "FAIL"}] {label}{suffix}')
        passed = sum(result[1] for result in self.results)
        print(f'\n{passed}/{len(self.results)} PASS')
        return passed == len(self.results)


def main(args=None):
    args = sys.argv if args is None else args
    options = parse_args(args)
    rclpy.init(args=args)
    node = P0Diagnostics()

    try:
        node.run(options)
        success = node.print_report()
    except KeyboardInterrupt:
        success = False
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()

    raise SystemExit(0 if success else 1)
