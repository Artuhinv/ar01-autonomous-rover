import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def launch_setup(context):
    description_dir = get_package_share_directory('ar01_description')
    simulation_dir = get_package_share_directory('ar01_simulation')
    ros_gz_sim_dir = get_package_share_directory('ros_gz_sim')

    world = LaunchConfiguration('world').perform(context)
    headless = LaunchConfiguration('headless').perform(context).lower() == 'true'
    controllers = os.path.join(simulation_dir, 'config', 'controllers.yaml')
    bridge_config = os.path.join(simulation_dir, 'config', 'bridge.yaml')
    xacro_file = os.path.join(description_dir, 'urdf', 'ar01.urdf.xacro')
    rviz_config = os.path.join(simulation_dir, 'rviz', 'ar01_sim.rviz')

    robot_description = ParameterValue(
        Command([
            'xacro ',
            xacro_file,
            ' use_sim:=true controller_config:=',
            controllers,
        ]),
        value_type=str,
    )

    gz_args = f'-r -v 3 {"-s " if headless else ""}{world}'
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_dir, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': gz_args,
            'on_exit_shutdown': 'true',
        }.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        output='screen',
        parameters=[{'config_file': bridge_config}],
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_ar01',
        output='screen',
        arguments=[
            '-world', 'p0_room',
            '-topic', '/robot_description',
            '-name', 'AR-01',
            '-allow_renaming', 'false',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.02',
        ],
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager', '/controller_manager',
            '--controller-manager-timeout', '60',
        ],
    )

    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=[
            'diff_drive_controller',
            '--controller-manager', '/controller_manager',
            '--controller-manager-timeout', '60',
            '--controller-ros-args',
            '--remap /diff_drive_controller/cmd_vel:=/cmd_vel '
            '--remap /diff_drive_controller/odom:=/odom',
        ],
    )

    start_joint_state_broadcaster = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_robot,
            on_exit=[joint_state_broadcaster_spawner],
        )
    )
    start_diff_drive_controller = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[diff_drive_controller_spawner],
        )
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('use_rviz')),
    )

    return [
        gazebo,
        clock_bridge,
        robot_state_publisher,
        spawn_robot,
        start_joint_state_broadcaster,
        start_diff_drive_controller,
        rviz,
    ]


def generate_launch_description():
    simulation_dir = get_package_share_directory('ar01_simulation')
    default_world = os.path.join(simulation_dir, 'worlds', 'p0_room.sdf')

    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value=default_world,
            description='Gazebo SDF world file.',
        ),
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description='Run Gazebo server without its graphical client.',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Start RViz2 with the AR-01 model and TF tree.',
        ),
        OpaqueFunction(function=launch_setup),
    ])
