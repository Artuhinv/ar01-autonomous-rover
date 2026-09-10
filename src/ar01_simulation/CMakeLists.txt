cmake_minimum_required(VERSION 3.8)
project(ar01_simulation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    config
    launch
    rviz
    worlds
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_simulation_assets test/test_simulation_assets.py)
endif()

ament_package()
