# AR-01 autonomous rover

Current milestone: **P0 simulation foundation, steps 0-19**.

Implemented now:

- ROS 2 Jazzy workspace for Ubuntu 24.04;
- `ar01_description`, `ar01_simulation`, and `ar01_tools` packages;
- primitive URDF/Xacro geometry and REP-103 frames;
- RViz model/TF launch and saved configuration;
- collision geometry, component masses, and analytical inertias;
- a 6 x 6 m Gazebo room with four walls and three obstacles;
- AR-01 spawning from `/robot_description`;
- `gz_ros2_control` velocity interfaces for both drive wheels;
- active joint-state and differential-drive controllers;
- `/cmd_vel`, `/odom`, `/joint_states`, `/tf`, and `/clock` runtime interfaces.

LiDAR/IMU plugins, sensor bridges, SLAM, Nav2, and autonomous behavior are
intentionally outside this milestone.

## Design baseline v0.1

| Parameter | Value |
| --- | ---: |
| Chassis | 320 x 280 x 100 mm |
| Wheels | 100 mm diameter x 25 mm width |
| Wheel track (centre-to-centre) | 310 mm |
| Drive axle from chassis centre | 25 mm forward |
| Caster | 25 mm radius |
| LiDAR frame from `base_footprint` | x=70, y=0, z=175 mm |
| IMU frame | chassis centre |
| Total modeled mass | 3.000 kg |

The 310 mm track preserves the previously checked wheel-frame positions at
`y=+/-155 mm` and provides 2.5 mm clearance between each wheel and the 280 mm
chassis. Confirm it against the real motor/wheel mounting before buying parts.

The rear caster and forward-shifted drive axle place the modeled centre of mass
inside the support triangle, instead of balancing the chassis on its front edge.

## Build and verify

```bash
cd ~/ar01_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash

xacro src/ar01_description/urdf/ar01.urdf.xacro > /tmp/ar01.urdf
check_urdf /tmp/ar01.urdf
colcon test --packages-select ar01_description
colcon test-result --verbose
ros2 launch ar01_description display.launch.py
```

For a lightweight TF check without WSLg windows:

```bash
ros2 launch ar01_description display.launch.py use_gui:=false use_rviz:=false
```

Run the current simulation milestone:

```bash
ros2 launch ar01_simulation sim.launch.py
```

For a lightweight WSL check without Gazebo/RViz windows:

```bash
ros2 launch ar01_simulation sim.launch.py headless:=true use_rviz:=false
```

In a second Ubuntu terminal, command a bounded forward motion (the tool always
publishes a stop command when it finishes):

```bash
source ~/ar01_ws/install/setup.bash
ros2 run ar01_tools cmd_test --linear 0.3 --duration 2.0
ros2 control list_controllers
ros2 topic echo /odom --once
```
