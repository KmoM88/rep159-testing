#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE_NAME="rep159-gazebo-topology-test:latest"

echo "=========================================================================="
echo " Building Docker Image: ${IMAGE_NAME}..."
echo "=========================================================================="
docker build -t "${IMAGE_NAME}" -f "${REPO_ROOT}/tests/real_world_gazebo/Dockerfile" "${REPO_ROOT}"

echo "=========================================================================="
echo " Running Gazebo + ROS Real-World Topology Test in Docker..."
echo "=========================================================================="
docker run --rm -t "${IMAGE_NAME}"
