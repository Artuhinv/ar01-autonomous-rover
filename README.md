# AR-01 autonomous rover

Frozen milestone: **P0 Digital AR-01 complete (steps 0-29)**.

Current design work: **P1 physical engineering, not yet P2**. P1.1 motor and
P1.2 driver are baselines; P1.3 portable C core passes host tests but lacks a
flashable STM32 adapter; P1.4 wheel-size screening prefers a 100 mm design
target but CAD is open; P1.5 staged sample/full-release rules are documented,
with all purchases still on hold. See [P1 release status](docs/P1_RELEASE.md)
and the [hardware BOM](hardware/BOM.csv). The
[NUCLEO board preflight](docs/P1_BOARD_PREFLIGHT.md) shows what is verified on
paper and what still needs CubeMX and bench evidence.
The [architecture decision register](docs/ARCHITECTURE_DECISIONS.md) separates
stable safety/interface properties from revisable part and technology baselines.

P0 provides a reproducible ROS 2 Jazzy + Gazebo Harmonic digital prototype:

- a physically modeled differential-drive robot with collision geometry,
  analytical inertias, a stable support polygon, LiDAR and IMU;
- a 6 x 6 m room with four walls and three obstacles;
- `gz_ros2_control`, active wheel controllers and odometry;
- one launch command for Gazebo, robot spawn, controllers, bridges and RViz;
- a ROS-only motion course and an automated 9/9 acceptance test.

EKF, SLAM, Nav2, autonomous behavior and physical hardware are intentionally
outside P0.

For a new Ubuntu 24.04 computer, follow the complete
[clean-machine setup guide](docs/SETUP.md) before using the commands below.

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
| LiDAR | 360 degrees, 720 samples, 10 Hz, 0.10-12.0 m |
| IMU | 100 Hz |

The 310 mm track preserves the previously checked wheel-frame positions at
`y=+/-155 mm` and provides 2.5 mm clearance between each wheel and the 280 mm
chassis. Confirm it against the real motor/wheel mounting before buying parts.

The rear caster and forward-shifted drive axle place the modeled centre of mass
inside the support triangle, instead of balancing the chassis on its front edge.

## Build

```bash
cd ~/ar01_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash

colcon test
colcon test-result --verbose
```

## Start P0

```bash
source /opt/ros/jazzy/setup.bash
source ~/ar01_ws/install/setup.bash
ros2 launch ar01_simulation sim.launch.py
```

This starts Gazebo, `p0_room`, AR-01, `robot_state_publisher`, both controllers,
the Gazebo-to-ROS bridges and RViz. For a machine without graphical windows:

```bash
ros2 launch ar01_simulation sim.launch.py headless:=true use_rviz:=false
```

## Verify P0

With the simulation running, use a second terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ar01_ws/install/setup.bash
ros2 run ar01_tools p0_diagnostics
```

The expected result is `9/9 PASS`. The check validates the robot description,
controllers, clock, joint states, odometry, LiDAR, IMU, forward motion, rotation,
finite numeric values and roll/pitch stability.

The repeatable ROS-only course is STOP -> 1 m -> 90 degrees -> 1 m -> STOP:

```bash
ros2 run ar01_tools cmd_test
```

Both tools communicate only through ROS interfaces and have no Gazebo-specific
API dependency.

## P0 interface contract

| Topic | Type | Producer / consumer |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/msg/TwistStamped` | command input to `diff_drive_controller` |
| `/odom` | `nav_msgs/msg/Odometry` | `diff_drive_controller` |
| `/joint_states` | `sensor_msgs/msg/JointState` | `joint_state_broadcaster` |
| `/scan` | `sensor_msgs/msg/LaserScan` | Gazebo GPU LiDAR bridge |
| `/imu/data` | `sensor_msgs/msg/Imu` | Gazebo IMU bridge |
| `/tf` | `tf2_msgs/msg/TFMessage` | dynamic transforms |
| `/tf_static` | `tf2_msgs/msg/TFMessage` | fixed robot transforms |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo simulation clock bridge |
| `/robot_description` | `std_msgs/msg/String` | `robot_state_publisher` |

The physical AR-01 should preserve this contract so higher-level ROS software
can move from simulation to hardware without changing its command logic.

## P1 physical design (no purchases yet)

P1 is design work, not a change to the frozen P0 simulation. See
[`docs/P1_REQUIREMENTS.md`](docs/P1_REQUIREMENTS.md) and
[`docs/P1_DRIVETRAIN.md`](docs/P1_DRIVETRAIN.md) for the motor baseline;
[`docs/P1_POWER.md`](docs/P1_POWER.md) for P1.2 current, driver and protection;
[`docs/P1_CONTROL.md`](docs/P1_CONTROL.md) for the provisional P1.3 STM32 pin
map and protocol; [`docs/P1_MECHANICAL.md`](docs/P1_MECHANICAL.md) for the
**open** P1.4 CAD gate; [`docs/P1_RELEASE.md`](docs/P1_RELEASE.md) for staged
P1.5/P2 gates; and [portable MCU code](firmware/ar01_controller/README.md).
Every physical BOM row remains `HOLD`.

On a machine with Python 3, P1 sizing is independent of ROS:

```bash
python3 hardware/calculations/drivetrain_sizing.py
python3 hardware/calculations/power_sizing.py
python3 -m unittest discover -s hardware/calculations -p 'test_*.py'
python3 -m unittest discover -s hardware/protocol -p 'test_*.py'
```
