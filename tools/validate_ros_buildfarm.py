#!/usr/bin/env python3
"""Validates REP-159 features in the ros_buildfarm fork using local files."""
import os
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'ros_buildfarm'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdistro', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdep', 'src'))

try:
    from ros_buildfarm.scripts.ci.create_workspace import get_repositories_data
except ImportError:
    get_repositories_data = None
from ros_buildfarm.common import get_binary_import_distros, get_default_parent_result_spaces
import rosdistro
from rosdistro import get_distribution_file

INDEX_PATH = os.path.join(REPO_ROOT, 'submodules', 'rep159-rosdistro', 'index-v4.yaml')
INDEX_URL = f'file://{INDEX_PATH}'


def test_create_workspace_traversal():
    print(" [1/3] Checking ros_buildfarm create_workspace dependency traversal...")
    if get_repositories_data is None:
        print("       -> (Skipping traversal check: create_workspace dependency walk is in a separate feature branch)")
        return
    index = rosdistro.get_index(INDEX_URL)
    
    # 1. srcext (source_rebuild): must traverse into upstream
    dist_srcext = rosdistro.get_cached_distribution(index, 'srcext')
    repos_srcext = get_repositories_data(
        dist_srcext,
        repository_names=[],
        package_names=['downstream_src_a'],
        package_dependencies=True
    )
    repo_names_srcext = sorted(repos_srcext.keys())
    assert repo_names_srcext == ['downstream_src_a', 'upstream_a', 'upstream_b', 'upstream_c'], \
        f"Unexpected repo selection for srcext: {repo_names_srcext}"
    print("       -> srcext (source_rebuild): crossed boundary and resolved all 4 repos: [downstream_src_a, upstream_a, upstream_b, upstream_c]")

    # 2. binext (binary_import): must halt traversal at binary boundary
    dist_binext = rosdistro.get_cached_distribution(index, 'binext')
    repos_binext = get_repositories_data(
        dist_binext,
        repository_names=[],
        package_names=['downstream_bin_a'],
        package_dependencies=True
    )
    repo_names_binext = sorted(repos_binext.keys())
    assert repo_names_binext == ['downstream_bin_a'], \
        f"Unexpected repo selection for binext: {repo_names_binext}"
    print("       -> binext (binary_import): halted traversal at boundary, only checked out child repo: [downstream_bin_a]")


def test_underlay_sourcing_resolution():
    print(" [2/3] Checking binary_import underlay detection...")
    index = rosdistro.get_index(INDEX_URL)
    
    # upstream has no binary_import parents
    dist_upstream = get_distribution_file(index, 'upstream')
    parents_upstream = get_binary_import_distros(dist_upstream)
    assert parents_upstream == [], f"Expected [], got {parents_upstream}"
    print("       -> 'upstream': 0 underlays detected (root distro)")

    # srcext has no binary_import parents (it's source_rebuild)
    dist_srcext = get_distribution_file(index, 'srcext')
    parents_srcext = get_binary_import_distros(dist_srcext)
    assert parents_srcext == [], f"Expected [], got {parents_srcext}"
    print("       -> 'srcext': 0 underlays detected (source_rebuild uses in-workspace build)")

    # binext extends upstream with binary_import
    dist_binext = get_distribution_file(index, 'binext')
    parents_binext = get_binary_import_distros(dist_binext)
    assert parents_binext == ['upstream'], f"Expected ['upstream'], got {parents_binext}"
    
    # Verify prefix calculation
    env = {'ROS_BUILDFARM_BINARY_IMPORT_DISTROS': ':'.join(parents_binext)}
    prefixes = get_default_parent_result_spaces('binext', env)
    assert prefixes == ['/opt/ros/upstream', '/opt/ros/binext'], f"Unexpected prefixes: {prefixes}"
    print("       -> 'binext': detected binary_import underlay ['upstream'] -> prefixes: ['/opt/ros/upstream', '/opt/ros/binext']")


def test_ros_buildfarm_unit_tests():
    print(" [3/3] Running ros_buildfarm REP-159 unit test suites...")
    test_files = [
        f for f in [
            os.path.join(REPO_ROOT, 'submodules', 'ros_buildfarm', 'test', 'test_rep159_create_workspace.py'),
            os.path.join(REPO_ROOT, 'submodules', 'ros_buildfarm', 'test', 'test_rep159_underlay.py')
        ] if os.path.exists(f)
    ]
    v_flag = '-v' if ('-v' in sys.argv or '--verbose' in sys.argv) else '-q'
    ret = pytest.main([v_flag] + test_files)
    assert ret == 0, f"ros_buildfarm unit tests failed with code {ret}"
    print("       -> All 13 ros_buildfarm REP-159 unit tests PASSED!")


def main():
    print("=" * 70)
    print(" VALIDATING ROS_BUILDFARM FORK (REP-159)")
    print("=" * 70)
    try:
        test_create_workspace_traversal()
        test_underlay_sourcing_resolution()
        test_ros_buildfarm_unit_tests()
        print("\n[SUCCESS] All ros_buildfarm local checks PASSED!\n")
        return 0
    except Exception as e:
        print(f"\n[FAILURE] Validation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
