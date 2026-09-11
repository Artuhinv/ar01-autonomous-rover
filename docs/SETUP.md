# AR-01 P0 clean-machine setup

This guide recreates the P0 development environment on a clean Ubuntu 24.04
(Noble) installation. ROS 2 Jazzy and Gazebo Harmonic are the supported pair.
Run all commands in Ubuntu, not in Windows PowerShell.

Official references:

- [ROS 2 Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [Gazebo Harmonic with ROS 2](https://gazebosim.org/docs/harmonic/ros_installation/)
- [Managing dependencies with rosdep](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Rosdep.html)
- [gz_ros2_control for Jazzy](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html)

## 1. Confirm the operating system

```bash
cat /etc/os-release
uname -m
```

The expected release is Ubuntu 24.04. Both `amd64` and `arm64` are supported by
ROS 2 Jazzy binary packages.

## 2. Add the ROS 2 apt repository

Set a UTF-8 locale and enable Ubuntu Universe:

```bash
sudo apt update
sudo apt install -y locales software-properties-common curl
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe
```

Install the current ROS repository configuration package:

```bash
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
```

## 3. Install ROS, Gazebo and control packages

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git ros-dev-tools ros-jazzy-desktop
sudo apt install -y ros-jazzy-ros-gz ros-jazzy-gz-ros2-control ros-jazzy-ros2-controllers
source /opt/ros/jazzy/setup.bash
```

`ros-jazzy-ros-gz` selects the Gazebo version paired with Jazzy, which is
Gazebo Harmonic. The last package supplies the differential-drive and
joint-state controllers used by AR-01.

## 4. Clone the P0 workspace

```bash
git clone https://github.com/Artuhinv/ar01-autonomous-rover.git ~/ar01_ws
cd ~/ar01_ws
```

The immutable `p0-digital-ar01` tag points to the completed P0 source snapshot.
Remain on `main` for this guide and the environment-check script: the tag is
intentionally not moved to include later documentation-only handoff commits.

## 5. Resolve declared dependencies

Initialize rosdep once on a new system. Skip `sudo rosdep init` if rosdep says
that its sources list already exists.

```bash
sudo rosdep init
rosdep update
cd ~/ar01_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
```

Nothing in this repository requires SLAM, Nav2 or an EKF for P0.

## 6. Check, build and test

```bash
cd ~/ar01_ws
source /opt/ros/jazzy/setup.bash
./scripts/check_environment.sh
colcon build --symlink-install
source install/setup.bash
colcon test
colcon test-result --verbose
```

The environment check does not install or modify anything. It verifies the OS,
ROS distribution, Gazebo major version, development commands, required ROS
packages and the dependency state reported by rosdep.

## 7. Start and accept P0

Graphical launch:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ar01_ws/install/setup.bash
ros2 launch ar01_simulation sim.launch.py
```

On a machine without usable graphics:

```bash
ros2 launch ar01_simulation sim.launch.py headless:=true use_rviz:=false
```

Keep the simulation running. In a second terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ar01_ws/install/setup.bash
ros2 run ar01_tools p0_diagnostics
```

The expected final line is:

```text
9/9 PASS
```

The optional ROS-only motion course is:

```bash
ros2 run ar01_tools cmd_test
```

## WSL 2 note

Ubuntu 24.04 under WSL 2 can run the same build and headless workflow. Gazebo
and RViz windows additionally require working WSLg/OpenGL support. If graphics
are unreliable, use the headless command above; the ROS interfaces and P0
diagnostics remain available.
