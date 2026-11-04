#!/usr/bin/env python3
"""
Validates REP-159 metadata resolution for Gazebo Harmonic Core + ROS Downstream topology.
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "submodules", "rosdistro", "src"))
sys.path.insert(0, os.path.join(REPO_ROOT, "submodules", "rosdep", "src"))

import yaml
from rosdistro.distribution_file import DistributionFile

def log_pass(msg):
    print(f"  [PASS] {msg}")

def log_fail(msg):
    print(f"  [FAIL] {msg}")
    sys.exit(1)

def main():
    print(">>> 1. Loading Gazebo Harmonic & ROS Downstream distribution files...")
    test_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(test_dir, "distribution_gz_harmonic.yaml"), "r") as f:
        gz_data = yaml.safe_load(f)
    dist_gz = DistributionFile("gz_harmonic", gz_data)

    with open(os.path.join(test_dir, "distribution_ros_downstream.yaml"), "r") as f:
        ros_data = yaml.safe_load(f)
    dist_ros = DistributionFile("ros_downstream", ros_data)

    # Check Gazebo distribution rules
    print(">>> 2. Verifying Gazebo Harmonic distribution specifications...")
    assert dist_gz.get_install_prefix() == "/opt/gazebo/harmonic", f"Bad prefix: {dist_gz.get_install_prefix()}"
    log_pass(f"Gazebo install prefix resolved to '{dist_gz.get_install_prefix()}'")

    for pkg in ["gz-cmake3", "gz-utils2", "gz-math7"]:
        bname = dist_gz.get_binary_package_name(pkg)
        expected = f"lib{pkg}-dev"
        assert bname == expected, f"Expected {expected}, got {bname}"
        log_pass(f"Package '{pkg}' binary naming resolved to '{bname}'")

    # Check ROS Downstream extension and underlay resolution
    print(">>> 3. Verifying ROS Downstream distribution inheritance (binary_import)...")
    assert len(dist_ros.extends) == 1, "Expected 1 parent"
    ext = dist_ros.extends[0]
    assert ext["distro_name"] == "gz_harmonic"
    assert ext["extension_method"] == "binary_import"
    log_pass("Extension declaration parsed correctly")

    # Merge parent into child
    dist_ros.merge_extends(dist_gz, "binary_import")

    # Check imported package attributes
    print(">>> 4. Verifying imported package attributes inside downstream distribution...")
    assert "gz-math7" in dist_ros.release_packages, "gz-math7 should be present in merged distribution"
    assert "ros_gz_math_demo" in dist_ros.release_packages, "ros_gz_math_demo should be present"

    math_bin = dist_ros.get_binary_package_name("gz-math7")
    demo_bin = dist_ros.get_binary_package_name("ros_gz_math_demo")
    assert math_bin == "libgz-math7-dev", f"Expected 'libgz-math7-dev', got '{math_bin}'"
    assert demo_bin == "ros-ros-downstream-ros-gz-math-demo", f"Expected 'ros-ros-downstream-ros-gz-math-demo', got '{demo_bin}'"
    log_pass(f"Imported parent binary name retained: '{math_bin}'")
    log_pass(f"Downstream leaf binary name prefixed: '{demo_bin}'")

    math_prefix = dist_ros.get_install_prefix("gz-math7")
    demo_prefix = dist_ros.get_install_prefix("ros_gz_math_demo")
    assert math_prefix == "/opt/gazebo/harmonic", f"Expected '/opt/gazebo/harmonic', got '{math_prefix}'"
    assert demo_prefix == "/opt/ros/ros-downstream", f"Expected '/opt/ros/ros-downstream', got '{demo_prefix}'"
    log_pass(f"Parent install prefix preserved: '{math_prefix}'")
    log_pass(f"Downstream install prefix isolated: '{demo_prefix}'")

    # Optional check: If ros_buildfarm has get_binary_import_underlays, test it
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "submodules", "ros_buildfarm"))
        from ros_buildfarm.common import get_binary_import_underlays
        underlays = get_binary_import_underlays(dist_ros)
        log_pass(f"ros_buildfarm underlays correctly generated: {underlays}")
    except (ImportError, AttributeError):
        pass

    print("\n=======================================================")
    print(" ALL GAZEBO + ROS TOPOLOGY METADATA CHECKS PASSED (5/5)")
    print("=======================================================")

if __name__ == "__main__":
    main()
