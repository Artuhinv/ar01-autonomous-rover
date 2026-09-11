#!/usr/bin/env bash

set -u

failures=0

pass() {
  printf '[PASS] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1"
  failures=$((failures + 1))
}

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "24.04" ]]; then
    pass "Ubuntu 24.04 (${PRETTY_NAME:-unknown})"
  else
    fail "Ubuntu 24.04 required; found ${PRETTY_NAME:-unknown OS}"
  fi
else
  fail "cannot read /etc/os-release"
fi

if [[ "${ROS_DISTRO:-}" == "jazzy" ]]; then
  pass "ROS_DISTRO=jazzy"
else
  fail "ROS 2 Jazzy is not sourced (run: source /opt/ros/jazzy/setup.bash)"
fi

for command_name in git ros2 colcon rosdep; do
  if command -v "${command_name}" >/dev/null 2>&1; then
    pass "command available: ${command_name}"
  else
    fail "command missing: ${command_name}"
  fi
done

if command -v gz >/dev/null 2>&1; then
  gazebo_version="$(gz sim --version 2>&1 | sed -n '1p')"
  if [[ "${gazebo_version}" =~ version[[:space:]]8\. ]]; then
    pass "Gazebo Harmonic (${gazebo_version})"
  else
    fail "Gazebo Harmonic major version 8 required; found ${gazebo_version:-unknown}"
  fi
else
  fail "Gazebo command missing: gz"
fi

required_ros_packages=(
  ament_cmake
  ament_index_python
  controller_manager
  controller_manager_msgs
  diff_drive_controller
  geometry_msgs
  gz_ros2_control
  joint_state_broadcaster
  joint_state_publisher
  joint_state_publisher_gui
  launch
  launch_ros
  nav_msgs
  rclpy
  robot_state_publisher
  ros_gz_bridge
  ros_gz_sim
  rosgraph_msgs
  rviz2
  sensor_msgs
  std_msgs
  xacro
)

if command -v ros2 >/dev/null 2>&1; then
  missing_packages=()
  for package_name in "${required_ros_packages[@]}"; do
    if ! ros2 pkg prefix "${package_name}" >/dev/null 2>&1; then
      missing_packages+=("${package_name}")
    fi
  done

  if ((${#missing_packages[@]} == 0)); then
    pass "all required ROS packages are installed"
  else
    fail "missing ROS packages: ${missing_packages[*]}"
  fi
else
  fail "required ROS packages cannot be checked without ros2"
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "${script_dir}/.." && pwd)"

if command -v rosdep >/dev/null 2>&1; then
  if rosdep_output="$(rosdep check --from-paths "${repository_root}/src" --ignore-src --rosdistro jazzy 2>&1)"; then
    pass "rosdep reports all package.xml dependencies satisfied"
  else
    fail "rosdep dependency check failed"
    printf '%s\n' "${rosdep_output}"
  fi
fi

if ((failures == 0)); then
  printf '\nAR-01 P0 environment ready\n'
  exit 0
fi

printf '\nAR-01 P0 environment has %d problem(s)\n' "${failures}"
exit 1
