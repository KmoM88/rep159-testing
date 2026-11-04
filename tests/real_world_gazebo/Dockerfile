FROM ubuntu:noble

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    pkg-config \
    libeigen3-dev \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-yaml \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install colcon
RUN pip install --no-cache-dir --break-system-packages --ignore-installed colcon-common-extensions

# Copy local ROS submodules with REP-159 support
COPY submodules/rosdistro /opt/ros_submodules/rosdistro
COPY submodules/ament_package /opt/ros_submodules/ament_package
COPY submodules/ament_cmake_core /opt/ros_submodules/ament_cmake_core
COPY submodules/ros_workspace /opt/ros_submodules/ros_workspace

# Copy distribution metadata definitions
COPY tests/real_world_gazebo/*.yaml /opt/distro_metadata/

# Copy downstream test packages
COPY tests/real_world_gazebo/packages /opt/test_packages

# Copy and set entrypoint script
COPY tests/real_world_gazebo/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
