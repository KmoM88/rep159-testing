cmake_minimum_required(VERSION 3.16)
project(ros_gz_math_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake_core REQUIRED)
find_package(gz-math7 REQUIRED)

add_executable(demo_node src/demo_node.cpp)
target_link_libraries(demo_node PRIVATE gz-math7::gz-math7)

install(TARGETS demo_node
  DESTINATION bin
)

ament_package()
