# AR-01 autonomous rover

Current milestone: **P0 description, steps 0-15**.

Implemented now:

- ROS 2 Jazzy workspace for Ubuntu 24.04;
- `ar01_description` and reserved `ar01_simulation` packages;
- primitive URDF/Xacro geometry and REP-103 frames;
- RViz model/TF launch and saved configuration;
- collision geometry, component masses, and analytical inertias.

Gazebo world, `ros2_control`, `/cmd_vel`, odometry, LiDAR/IMU plugins,
bridges, and navigation are intentionally outside this milestone.

## Design baseline v0.1

| Parameter | Value |
| --- | ---: |
| Chassis | 320 x 280 x 100 mm |
| Wheels | 100 mm diameter x 25 mm width |
| Wheel track (centre-to-centre) | 310 mm |
| Caster | 25 mm radius |
| LiDAR frame from `base_footprint` | x=70, y=0, z=175 mm |
| IMU frame | chassis centre |
| Total modeled mass | 3.000 kg |

The 310 mm track preserves the previously checked wheel-frame positions at
`y=+/-155 mm` and provides 2.5 mm clearance between each wheel and the 280 mm
chassis. Confirm it against the real motor/wheel mounting before buying parts.

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
