#!/usr/bin/env python3
"""
Validates the declarative regex-based binary package naming engine
(Feature 1: exploration/binary-naming-regex) in rosdistro and rosdep.
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdistro', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdep', 'src'))

from rosdistro.distribution_file import DistributionFile
from rosdistro.release_repository_specification import ReleaseRepositorySpecification
from rosdep2.gbpdistro_support import get_gbprepo_as_rosdep_data


def test_standard_default_naming():
    print(" • [1/6] Standard default naming (ros-{distro}-{pkg} with _ -> - sanitization)...")
    data = {
        'url': 'https://github.com/ros2-gbp/common_interfaces-release.git',
        'version': '5.9.2-2',
        'tags': {'release': 'release/rolling/{package}/{version}'},
        'packages': ['std_msgs', 'sensor_msgs']
    }
    repo = ReleaseRepositorySpecification('common_interfaces', data)
    repo.origin_distro = 'lyrical'

    assert repo.get_binary_package_name('std_msgs') == 'ros-lyrical-std-msgs'
    assert repo.get_binary_package_name('sensor_msgs') == 'ros-lyrical-sensor-msgs'
    print("   -> std_msgs -> ros-lyrical-std-msgs (OK)")
    print("   -> sensor_msgs -> ros-lyrical-sensor-msgs (OK)")


def test_prefix_rule():
    print(" • [2/6] Custom vendor prefix rule (search: '^', replace: 'acme-{distro}-')...")
    data = {
        'url': 'https://github.com/acme/teleop-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['teleop_twist_keyboard'],
        'binary_rule': {
            'search': '^',
            'replace': 'acme-{distro}-'
        }
    }
    repo = ReleaseRepositorySpecification('teleop', data)
    repo.origin_distro = 'jazzy'

    binary_name = repo.get_binary_package_name('teleop_twist_keyboard')
    assert binary_name == 'acme-jazzy-teleop-twist-keyboard'
    print(f"   -> teleop_twist_keyboard -> {binary_name} (OK)")


def test_exact_binary_override():
    print(" • [3/6] Exact binary override rule (gz-cmake -> libgz-cmake5-dev)...")
    data = {
        'url': 'https://github.com/gazebosim/gz-cmake-release.git',
        'version': '5.1.1-2',
        'tags': {'release': 'gz-cmake5_{version}'},
        'packages': ['gz-cmake'],
        'binary_rule': {
            'search': '^gz-cmake$',
            'replace': 'libgz-cmake5-dev'
        }
    }
    repo = ReleaseRepositorySpecification('gz-cmake', data)
    repo.origin_distro = 'jetty'

    binary_name = repo.get_binary_package_name('gz-cmake')
    assert binary_name == 'libgz-cmake5-dev'
    print(f"   -> gz-cmake -> {binary_name} (OK)")


def test_unprefixed_no_op_rule():
    print(" • [4/6] Native / Unprefixed rule (search: '^', replace: '')...")
    data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '10.5.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim10'],
        'binary_rule': {
            'search': '^',
            'replace': ''
        }
    }
    repo = ReleaseRepositorySpecification('gz_sim', data)
    repo.origin_distro = 'jetty'

    binary_name = repo.get_binary_package_name('gz_sim10')
    assert binary_name == 'gz-sim10'
    print(f"   -> gz_sim10 -> {binary_name} (OK)")


def test_regex_group_capture_rewrite():
    print(" • [5/6] Regex group capture & rewriting (search: '^nav2-(.*)$', replace: 'corp-{distro}-navigation-\\1')...")
    data = {
        'url': 'https://github.com/corp/nav2-release.git',
        'version': '2.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['nav2_planner', 'nav2_controller'],
        'binary_rule': {
            'search': '^nav2-(.*)$',
            'replace': 'corp-{distro}-navigation-\\1'
        }
    }
    repo = ReleaseRepositorySpecification('corp_nav', data)
    repo.origin_distro = 'humble'

    b1 = repo.get_binary_package_name('nav2_planner')
    b2 = repo.get_binary_package_name('nav2_controller')
    assert b1 == 'corp-humble-navigation-planner'
    assert b2 == 'corp-humble-navigation-controller'
    print(f"   -> nav2_planner -> {b1} (OK)")
    print(f"   -> nav2_controller -> {b2} (OK)")


def test_rosdep_delegation():
    print(" • [6/6] End-to-end rosdep delegation with custom binary_rule...")
    distro_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['resolute']},
        'repositories': {
            'custom_pkg': {
                'release': {
                    'url': 'https://github.com/org/custom-release.git',
                    'version': '1.0.0-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['custom_driver'],
                    'binary_rule': {
                        'search': '^',
                        'replace': 'robotics-{distro}-'
                    }
                }
            }
        }
    }
    distro = DistributionFile('testdistro', distro_data)
    distro.repositories['custom_pkg'].release_repository.origin_distro = 'testdistro'

    import rosdep2.gbpdistro_support
    from rosdep2.rosdistrohelper import ReleaseFile
    original_get_release_file = rosdep2.gbpdistro_support.get_release_file
    try:
        rosdep2.gbpdistro_support.get_release_file = lambda d: ReleaseFile(distro)
        rosdep_data = get_gbprepo_as_rosdep_data('testdistro')
    finally:
        rosdep2.gbpdistro_support.get_release_file = original_get_release_file

    assert 'custom_driver' in rosdep_data
    resolved_apt_pkgs = rosdep_data['custom_driver']['ubuntu']['resolute']['apt']['packages']
    assert resolved_apt_pkgs == ['robotics-testdistro-custom-driver']
    print(f"   -> rosdep resolved: custom_driver => {resolved_apt_pkgs} (OK)")


def main():
    print("=" * 70)
    print(" VALIDATING BINARY PACKAGE RENAMING ENGINE (REGEX)")
    print("=" * 70)
    if not hasattr(ReleaseRepositorySpecification, 'get_binary_package_name'):
        print("\n [INFO] Feature 1 (Binary Package Renaming Engine) is not present in")
        print("        the currently active rosdistro branch.")
        print("        To run this validation suite, switch rosdistro to the feature branch:")
        print("          git -C submodules/rosdistro checkout exploration/binary-naming-regex")
        print("          ./tools/run_all_validations.sh --suite 6\n")
        return 0

    try:
        test_standard_default_naming()
        test_prefix_rule()
        test_exact_binary_override()
        test_unprefixed_no_op_rule()
        test_regex_group_capture_rewrite()
        test_rosdep_delegation()
        print("\n[SUCCESS] All binary package naming (regex) checks PASSED 100%!\n")
        return 0
    except Exception as e:
        print(f"\n[FAILURE] Binary naming validation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
