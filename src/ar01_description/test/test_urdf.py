import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest


XACRO_FILE = Path(__file__).parents[1] / 'urdf' / 'ar01.urdf.xacro'
PHYSICAL_LINKS = {
    'base_link',
    'left_wheel_link',
    'right_wheel_link',
    'caster_link',
    'lidar_link',
    'imu_link',
}


def robot_root(*xacro_args):
    result = subprocess.run(
        ['xacro', str(XACRO_FILE), *xacro_args],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def xyz(root, joint_name):
    joint = root.find(f"joint[@name='{joint_name}']")
    return [float(value) for value in joint.find('origin').attrib['xyz'].split()]


def test_expected_kinematic_tree_and_origins():
    root = robot_root()
    links = {link.attrib['name'] for link in root.findall('link')}
    joints = {joint.attrib['name'] for joint in root.findall('joint')}

    assert links == PHYSICAL_LINKS | {'base_footprint'}
    assert joints == {
        'base_footprint_joint',
        'left_wheel_joint',
        'right_wheel_joint',
        'caster_joint',
        'lidar_joint',
        'imu_joint',
    }
    assert xyz(root, 'base_footprint_joint') == pytest.approx([0.0, 0.0, 0.100])
    assert xyz(root, 'lidar_joint') == pytest.approx([0.070, 0.0, 0.075])
    assert xyz(root, 'imu_joint') == pytest.approx([-0.025, 0.0, 0.0])
    assert xyz(root, 'left_wheel_joint') == pytest.approx([0.0, 0.155, -0.050])
    assert xyz(root, 'right_wheel_joint') == pytest.approx([0.0, -0.155, -0.050])


def test_every_physical_link_has_valid_rigid_body_data():
    root = robot_root()
    links = {link.attrib['name']: link for link in root.findall('link')}
    total_mass = 0.0

    for name in PHYSICAL_LINKS:
        link = links[name]
        assert link.find('visual') is not None
        assert link.find('collision') is not None

        inertial = link.find('inertial')
        assert inertial is not None
        mass = float(inertial.find('mass').attrib['value'])
        assert math.isfinite(mass) and mass > 0.0
        total_mass += mass

        inertia = inertial.find('inertia').attrib
        diagonal = [float(inertia[key]) for key in ('ixx', 'iyy', 'izz')]
        assert all(math.isfinite(value) and value > 0.0 for value in diagonal)
        assert diagonal[0] + diagonal[1] >= diagonal[2]
        assert diagonal[0] + diagonal[2] >= diagonal[1]
        assert diagonal[1] + diagonal[2] >= diagonal[0]

    assert total_mass == pytest.approx(3.000)


def test_simulation_exports_two_velocity_controlled_wheel_joints():
    root = robot_root('use_sim:=true', 'controller_config:=/tmp/controllers.yaml')
    control = root.find("ros2_control[@name='GazeboSimSystem']")
    assert control is not None
    assert control.findtext('hardware/plugin') == 'gz_ros2_control/GazeboSimSystem'

    joints = {joint.attrib['name']: joint for joint in control.findall('joint')}
    assert set(joints) == {'left_wheel_joint', 'right_wheel_joint'}
    for joint in joints.values():
        assert [item.attrib['name'] for item in joint.findall('command_interface')] == [
            'velocity'
        ]
        assert [item.attrib['name'] for item in joint.findall('state_interface')] == [
            'position',
            'velocity',
        ]

    plugin = root.find('gazebo/plugin')
    assert plugin.attrib['filename'] == 'libgz_ros2_control-system.so'
    assert plugin.attrib['name'] == 'gz_ros2_control::GazeboSimROS2ControlPlugin'
    assert plugin.findtext('parameters') == '/tmp/controllers.yaml'

    lidar = root.find("gazebo[@reference='lidar_link']/sensor[@name='gpu_lidar']")
    assert lidar is not None
    assert lidar.attrib['type'] == 'gpu_lidar'
    assert lidar.findtext('topic') == '/scan'
    assert int(lidar.findtext('lidar/scan/horizontal/samples')) == 720
    assert float(lidar.findtext('lidar/range/min')) == pytest.approx(0.10)
    assert float(lidar.findtext('lidar/range/max')) == pytest.approx(12.0)

    imu = root.find("gazebo[@reference='imu_link']/sensor[@name='imu_sensor']")
    assert imu is not None
    assert imu.attrib['type'] == 'imu'
    assert imu.findtext('topic') == '/imu/data'
    assert float(imu.findtext('update_rate')) == pytest.approx(100.0)
