#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================================="
echo " Starting REP-159 Real-World Topology Test: Gazebo Harmonic + ROS 2       "
echo "=========================================================================="

WORKSPACE_DIR="/workspace"
GAZEBO_SRC="${WORKSPACE_DIR}/gazebo_ws/src"
GAZEBO_INSTALL="/opt/gazebo/harmonic"
ROS_INSTALL="/opt/ros/jazzy_custom"

mkdir -p "${GAZEBO_SRC}"
mkdir -p "${GAZEBO_INSTALL}"
mkdir -p "${ROS_INSTALL}"

# Step 1: Clone Gazebo Harmonic Core libraries
echo ">>> [1/5] Fetching real Gazebo Harmonic Core packages (git tags)..."
if [ ! -d "${GAZEBO_SRC}/gz-cmake" ]; then
    git clone --depth 1 -b gz-cmake3_3.5.4 https://github.com/gazebosim/gz-cmake.git "${GAZEBO_SRC}/gz-cmake"
fi
if [ ! -d "${GAZEBO_SRC}/gz-utils" ]; then
    git clone --depth 1 -b gz-utils2_2.2.1 https://github.com/gazebosim/gz-utils.git "${GAZEBO_SRC}/gz-utils"
fi
if [ ! -d "${GAZEBO_SRC}/gz-math" ]; then
    git clone --depth 1 -b gz-math7_7.5.0 https://github.com/gazebosim/gz-math.git "${GAZEBO_SRC}/gz-math"
fi

# Step 2: Build and Install Gazebo Harmonic Core to /opt/gazebo/harmonic
echo ">>> [2/5] Compiling Gazebo Harmonic Core into ${GAZEBO_INSTALL}..."
cd "${WORKSPACE_DIR}/gazebo_ws"
colcon build \
    --merge-install \
    --install-base "${GAZEBO_INSTALL}" \
    --cmake-args \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF \
        -DCMAKE_INSTALL_PREFIX="${GAZEBO_INSTALL}"

echo "Gazebo libraries successfully installed:"
ls -lh "${GAZEBO_INSTALL}/lib" || true

# Step 3: Install ament_package, ament_cmake_core and ros_workspace into /opt/ros/jazzy_custom
echo ">>> [3/5] Setting up ROS Underlay Chaining via ros_workspace (REP-159)..."
# 1. Install ament_package system-wide so python3 can import it anywhere
pip install --no-cache-dir --break-system-packages /opt/ros_submodules/ament_package

# 2. Make ament_package visible in the ROS prefix for ros_workspace template discovery
mkdir -p "${ROS_INSTALL}/lib/python3.12/site-packages"
cp -r /opt/ros_submodules/ament_package/ament_package "${ROS_INSTALL}/lib/python3.12/site-packages/"

# Install ament_cmake_core
mkdir -p /tmp/build_ament_cmake
cd /tmp/build_ament_cmake
cmake /opt/ros_submodules/ament_cmake_core \
    -DCMAKE_INSTALL_PREFIX="${ROS_INSTALL}"
cmake --build . --target install

# Install ros_workspace with ROS_WORKSPACE_PARENT_PREFIX_PATH pointing to /opt/gazebo/harmonic
mkdir -p /tmp/build_ros_workspace
cd /tmp/build_ros_workspace
cmake /opt/ros_submodules/ros_workspace \
    -DCMAKE_INSTALL_PREFIX="${ROS_INSTALL}" \
    -DROS_WORKSPACE_PARENT_PREFIX_PATH="${GAZEBO_INSTALL}" \
    -DAMENT_CMAKE_ENVIRONMENT_PARENT_PREFIX_PATH_GENERATION=OFF
cmake --build . --target install

echo "Checking parent_prefix_path resource in ros_workspace:"
cat "${ROS_INSTALL}/share/ament_index/resource_index/parent_prefix_path/ros_workspace"
echo ""

# Step 4: Sourcing downstream environment and validating underlay chain
echo ">>> [4/5] Verifying environment underlay chaining..."
set +u
source "${ROS_INSTALL}/setup.sh"
set -u

echo "CMAKE_PREFIX_PATH: ${CMAKE_PREFIX_PATH}"
echo "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-}"

if [[ ":${CMAKE_PREFIX_PATH}:" != *":${GAZEBO_INSTALL}:"* ]]; then
    echo "ERROR: ${GAZEBO_INSTALL} was not chained into CMAKE_PREFIX_PATH!"
    exit 1
fi

# Step 5: Compiling downstream C++ leaf package (ros_gz_math_demo)
echo ">>> [5/5] Compiling and running downstream ROS 2 package (ros_gz_math_demo)..."
mkdir -p "${WORKSPACE_DIR}/ros_ws/src"
cp -r /opt/test_packages/ros_gz_math_demo "${WORKSPACE_DIR}/ros_ws/src/"
cd "${WORKSPACE_DIR}/ros_ws"

colcon build \
    --merge-install \
    --install-base "${ROS_INSTALL}" \
    --cmake-args \
        -DCMAKE_BUILD_TYPE=Release \
        -Dament_cmake_core_DIR="${ROS_INSTALL}/share/ament_cmake_core/cmake"

echo "Executing test binary linked against Gazebo Harmonic underlay:"
"${ROS_INSTALL}/bin/demo_node"

echo "=========================================================================="
echo " REAL-WORLD TOPOLOGY VERIFICATION SUCCESSFUL! (Gazebo + ROS 2 Chained)   "
echo "=========================================================================="
