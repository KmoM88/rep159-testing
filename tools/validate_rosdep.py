#!/usr/bin/env python3
"""Validates REP-159 features in the rosdep fork using local tests."""
import os
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdistro', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdep', 'src'))

from rosdep2.gbpdistro_support import get_gbprepo_as_rosdep_data


def test_binary_import_vs_source_rebuild_resolution():
    print(" [1/2] Checking rosdep binary resolution for binary_import vs source_rebuild...")
    # Use rosdep's test fixture fake rosdistro index
    test_dir = os.path.join(REPO_ROOT, 'submodules', 'rosdep', 'test')
    fake_index_url = 'file://' + os.path.abspath(os.path.join(test_dir, 'fake_rosdistro', 'index-v4.yaml'))
    
    os.environ['ROSDISTRO_INDEX_URL'] = fake_index_url
    
    # 1. binary_import: 'ros' is imported from 'z_base'
    data_bin = get_gbprepo_as_rosdep_data('z_derived_binary')
    assert 'ros' in data_bin, "Expected 'ros' package in rosdep data"
    assert data_bin['ros']['ubuntu']['bionic']['apt']['packages'] == ['ros-z-base-ros']
    # 'new_package' originates in 'z_derived_binary'
    assert data_bin['new_package']['ubuntu']['bionic']['apt']['packages'] == ['ros-z-derived-binary-new-package']
    print("       -> binary_import: 'ros' resolves to parent binary 'ros-z-base-ros'")
    print("       -> binary_import: 'new_package' resolves to child binary 'ros-z-derived-binary-new-package'")

    # 2. source_rebuild: 'ros' is inherited from base and rebuilt under derived name
    data_src = get_gbprepo_as_rosdep_data('z_derived_source')
    assert 'ros' in data_src
    assert data_src['ros']['ubuntu']['bionic']['apt']['packages'] == ['ros-z-derived-source-ros']
    print("       -> source_rebuild: 'ros' resolves to child rebuilt binary 'ros-z-derived-source-ros'")


def test_rosdep_unit_test_suite():
    print(" [2/2] Running rosdep REP-159 gbpdistro test suite...")
    test_file = os.path.join(REPO_ROOT, 'submodules', 'rosdep', 'test', 'test_rosdep_gbpdistro_support.py')
    v_flag = '-v' if ('-v' in sys.argv or '--verbose' in sys.argv) else '-q'
    ret = pytest.main([v_flag, '-k', 'binary_import or source_rebuild', test_file])
    assert ret == 0, f"rosdep unit tests failed with code {ret}"
    print("       -> All rosdep REP-159 tests PASSED!")


def main():
    print("=" * 70)
    print(" VALIDATING ROSDEP FORK (REP-159)")
    print("=" * 70)
    try:
        test_binary_import_vs_source_rebuild_resolution()
        test_rosdep_unit_test_suite()
        print("\n[SUCCESS] All rosdep local checks PASSED!\n")
        return 0
    except Exception as e:
        print(f"\n[FAILURE] Validation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
