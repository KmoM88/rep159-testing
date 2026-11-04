#!/usr/bin/env bash
# Generates Gazebo Harmonic + ROS Downstream jobs on Jenkins
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_INDEX="file://${REPO_ROOT}/buildfarm/real_world_gazebo/index-local-gazebo.yaml"

echo "=========================================================================="
echo " Generating Jenkins Jobs for Gazebo Harmonic + ROS Downstream Topology    "
echo "=========================================================================="

echo ">>> [1/3] Generating Gazebo Harmonic release jobs (Sourcedeb/Binarydeb)..."
"${REPO_ROOT}/.venv/bin/python" -m ros_buildfarm.scripts.release.generate_release_jobs \
    "${CONFIG_INDEX}" gz_harmonic default

echo ">>> [2/3] Generating Gazebo Harmonic CI job..."
"${REPO_ROOT}/.venv/bin/python" -m ros_buildfarm.scripts.ci.generate_ci_jobs \
    "${CONFIG_INDEX}" gz_harmonic

echo ">>> [3/3] Generating Downstream ROS CI job (binary_import)..."
"${REPO_ROOT}/.venv/bin/python" -m ros_buildfarm.scripts.ci.generate_ci_jobs \
    "${CONFIG_INDEX}" ros_downstream

echo "=========================================================================="
echo " Job generation complete! Check Jenkins dashboard.                       "
echo "=========================================================================="
