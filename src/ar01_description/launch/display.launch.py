from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition, UnlessCondition
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import os


def generate_launch_description():
    package_dir = get_package_share_directory('ar01_description')
    xacro_file = os.path.join(package_dir, 'urdf', 'ar01.urdf.xacro')
    default_rviz_config = os.path.join(package_dir, 'rviz', 'ar01.rviz')

    use_gui = LaunchConfiguration('use_gui')
    use_rviz = LaunchConfiguration('use_rviz')
    rviz_config = LaunchConfiguration('rviz_config')

    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        output='screen',
        parameters=[{'robot_description': robot_description}],
        condition=IfCondition(use_gui),
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
        condition=UnlessCondition(use_gui),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gui',
            default_value='true',
            description='Use joint_state_publisher_gui instead of the headless publisher.',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Start RViz2.',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=default_rviz_config,
            description='RViz2 configuration file.',
        ),
        robot_state_publisher,
        joint_state_publisher_gui,
        joint_state_publisher,
        rviz,
    ])
