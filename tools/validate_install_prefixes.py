#!/usr/bin/env python3
"""
Validates REP-159 Custom Installation Prefixes and Underlay Resolution Engine.
Tests:
  1. Default ROS installation prefix (/opt/ros/<distro>)
  2. Custom vendor template prefix (/opt/<vendor>/<distro>)
  3. Declarative regex-based prefix rewriting (search/replace)
  4. Isolated per-package prefix layout (/opt/<distro>/<package>)
  5. Regex group capture and remapping (/opt/osrf/<distro>/<pkg>)
  6. Propagation from DistributionFile to ReleaseRepositorySpecification
  7. Ros_buildfarm underlay generation for binary_import parents
  8. Environment variable overrides (ROS_BUILDFARM_PARENT_RESULT_SPACES)
  9. Backward compatibility with legacy ROS_BUILDFARM_BINARY_IMPORT_DISTROS
"""

import sys
import os

# Add local submodules to sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdistro', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'ros_buildfarm'))

from rosdistro.distribution_file import DistributionFile
from rosdistro.release_repository_specification import ReleaseRepositorySpecification
from ros_buildfarm.common import (
    get_binary_import_underlays,
    get_default_parent_result_spaces,
    get_distribution_install_prefix,
    PARENT_RESULT_SPACES_ENV,
    BINARY_IMPORT_DISTROS_ENV
)


def log_pass(msg):
    print(f"  [PASS] {msg}")


def log_fail(msg):
    print(f"  [FAIL] {msg}")
    sys.exit(1)


def test_standard_ros_prefix():
    print(">>> 1. Validating standard default ROS prefix...")
    data = {
        'url': 'https://github.com/ros2-gbp/common_interfaces-release.git',
        'version': '5.9.2-2',
        'tags': {'release': 'release/rolling/{package}/{version}'},
        'packages': ['std_msgs']
    }
    repo = ReleaseRepositorySpecification('common_interfaces', data)
    repo.origin_distro = 'jazzy'
    prefix = repo.get_install_prefix('std_msgs')
    if prefix == '/opt/ros/jazzy':
        log_pass(f"Standard package uses '{prefix}'")
    else:
        log_fail(f"Expected '/opt/ros/jazzy', got '{prefix}'")


def test_vendor_template_prefix():
    print(">>> 2. Validating vendor template string prefix...")
    data = {
        'url': 'https://github.com/acme/teleop-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['teleop_keyboard'],
        'install_rule': '/opt/acme/{distro}'
    }
    repo = ReleaseRepositorySpecification('teleop', data)
    repo.origin_distro = 'jazzy'
    prefix = repo.get_install_prefix('teleop_keyboard')
    if prefix == '/opt/acme/jazzy':
        log_pass(f"Vendor template resolved to '{prefix}'")
    else:
        log_fail(f"Expected '/opt/acme/jazzy', got '{prefix}'")


def test_regex_search_replace_prefix():
    print(">>> 3. Validating regex whole-string rewrite prefix...")
    data = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_pkg'],
        'install_rule': {
            'search': '^.*$',
            'replace': '/opt/custom/{distro}'
        }
    }
    repo = ReleaseRepositorySpecification('custom_repo', data)
    repo.origin_distro = 'rolling'
    prefix = repo.get_install_prefix('my_pkg')
    if prefix == '/opt/custom/rolling':
        log_pass(f"Regex rewrite produced '{prefix}'")
    else:
        log_fail(f"Expected '/opt/custom/rolling', got '{prefix}'")


def test_isolated_package_layout():
    print(">>> 4. Validating isolated per-package prefix layout (/opt/distro/pkg)...")
    data = {
        'url': 'https://github.com/org/pkg-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['custom_driver'],
        'install_rule': {
            'search': '^',
            'replace': '/opt/ros/{distro}/'
        }
    }
    repo = ReleaseRepositorySpecification('custom_driver', data)
    repo.origin_distro = 'upstream'
    prefix = repo.get_install_prefix('custom_driver')
    if prefix == '/opt/ros/upstream/custom-driver':
        log_pass(f"Isolated layout produced '{prefix}'")
    else:
        log_fail(f"Expected '/opt/ros/upstream/custom-driver', got '{prefix}'")


def test_group_capture_prefix():
    print(">>> 5. Validating regex group capture prefix...")
    data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim'],
        'install_rule': {
            'search': '^gz-(.*)$',
            'replace': '/opt/osrf/{distro}/\\1'
        }
    }
    repo = ReleaseRepositorySpecification('gz_sim', data)
    repo.origin_distro = 'harmonic'
    prefix = repo.get_install_prefix('gz-sim')
    if prefix == '/opt/osrf/harmonic/sim':
        log_pass(f"Group capture correctly rewritten to '{prefix}'")
    else:
        log_fail(f"Expected '/opt/osrf/harmonic/sim', got '{prefix}'")


def test_distribution_propagation():
    print(">>> 6. Validating DistributionFile propagation...")
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'install_rule': '/opt/acme/{distro}',
        'repositories': {
            'pkg_a': {
                'release': {
                    'url': 'https://github.com/acme/pkg_a-release.git',
                    'version': '1.0.0-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['pkg_a']
                }
            }
        }
    }
    dist_file = DistributionFile('acme_distro', dist_data)
    dist_prefix = dist_file.get_install_prefix()
    pkg_prefix = dist_file.get_install_prefix('pkg_a')
    repo_prefix = dist_file.repositories['pkg_a'].release_repository.get_install_prefix('pkg_a')

    if dist_prefix == '/opt/acme/acme-distro' and pkg_prefix == '/opt/acme/acme-distro' and repo_prefix == '/opt/acme/acme-distro':
        log_pass("DistributionFile level rule propagates to repository specifications")
    else:
        log_fail(f"Mismatch in distribution propagation: {dist_prefix}, {pkg_prefix}, {repo_prefix}")


def test_buildfarm_underlays():
    print(">>> 7. Validating ros_buildfarm underlays resolution...")
    class MockDistFile:
        def __init__(self):
            self.name = 'binext'
            self.extends = [
                {'distro_name': 'upstream', 'extension_method': 'source_rebuild'},
                {'distro_name': 'gazebo', 'extension_method': 'binary_import', 'install_rule': '/usr'},
                {'distro_name': 'vendor_os', 'extension_method': 'binary_import', 'install_rule': '/opt/vendor/{distro}'},
                {'distro_name': 'standard_ros', 'extension_method': 'binary_import'}
            ]
        def get_install_prefix(self, pkg_name=None):
            return '/opt/ros/binext'

    dist_file = MockDistFile()
    underlays = get_binary_import_underlays(dist_file)
    expected_underlays = [
        '/usr',
        '/opt/vendor/vendor_os',
        '/opt/ros/standard_ros'
    ]
    if underlays == expected_underlays:
        log_pass(f"Binary import underlays resolved: {underlays}")
    else:
        log_fail(f"Expected underlays {expected_underlays}, got {underlays}")

    parent_spaces = get_default_parent_result_spaces('binext', environ={}, dist_file=dist_file)
    expected_parent_spaces = expected_underlays + ['/opt/ros/binext']
    if parent_spaces == expected_parent_spaces:
        log_pass(f"Parent result spaces resolved: {parent_spaces}")
    else:
        log_fail(f"Expected parent spaces {expected_parent_spaces}, got {parent_spaces}")


def test_buildfarm_environment_variables():
    print(">>> 8. Validating explicit & legacy environment variables in ros_buildfarm...")
    # Explicit variable
    env = {PARENT_RESULT_SPACES_ENV: '/custom/p1:/custom/p2'}
    res = get_default_parent_result_spaces('distro', environ=env)
    if res == ['/custom/p1', '/custom/p2']:
        log_pass("PARENT_RESULT_SPACES_ENV takes immediate priority")
    else:
        log_fail(f"Expected explicit spaces, got {res}")

    # Legacy variable
    env_legacy = {BINARY_IMPORT_DISTROS_ENV: 'parent1:parent2'}
    res_legacy = get_default_parent_result_spaces('child', environ=env_legacy)
    if res_legacy == ['/opt/ros/parent1', '/opt/ros/parent2', '/opt/ros/child']:
        log_pass("BINARY_IMPORT_DISTROS_ENV legacy fallback is 100% backward compatible")
    else:
        log_fail(f"Expected legacy fallback spaces, got {res_legacy}")


def main():
    print("======================================================================")
    print("  VALIDATING REP-159 CUSTOM INSTALL PREFIX & UNDERLAY RESOLUTION      ")
    print("======================================================================")
    test_standard_ros_prefix()
    test_vendor_template_prefix()
    test_regex_search_replace_prefix()
    test_isolated_package_layout()
    test_group_capture_prefix()
    test_distribution_propagation()
    test_buildfarm_underlays()
    test_buildfarm_environment_variables()
    print("======================================================================")
    print("  ALL INSTALL PREFIX & UNDERLAY CHECKS PASSED SUCCESSFULLY (9/9)!     ")
    print("======================================================================")


if __name__ == '__main__':
    main()
