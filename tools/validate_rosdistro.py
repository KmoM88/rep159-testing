#!/usr/bin/env python3
"""Validates REP-159 features and edge cases in the rosdistro fork using local files."""
import os
import sys

# Ensure local forks are imported
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdistro', 'src'))

import rosdistro
from rosdistro import get_distribution_file
from rosdistro.distribution_file import DistributionFile

INDEX_PATH = os.path.join(REPO_ROOT, 'submodules', 'rep159-rosdistro', 'index-v4.yaml')
INDEX_URL = f'file://{INDEX_PATH}'


def test_format_3_parsing():
    print(" [1/6] Checking index-v4.yaml format 3 parsing...")
    index = rosdistro.get_index(INDEX_URL)
    assert 'upstream' in index.distributions, "Missing 'upstream' in index"
    assert 'srcext' in index.distributions, "Missing 'srcext' in index"
    assert 'binext' in index.distributions, "Missing 'binext' in index"
    print("       -> Successfully parsed distributions: upstream, srcext, binext")


def test_extension_definitions():
    print(" [2/6] Checking distribution extension definitions...")
    index = rosdistro.get_index(INDEX_URL)
    
    # upstream: root distro
    dist_upstream = get_distribution_file(index, 'upstream')
    assert dist_upstream.version == 3, f"Expected version 3, got {dist_upstream.version}"
    assert not getattr(dist_upstream, 'extends', []), "upstream should not extend any distro"
    print("       -> 'upstream': verified as root distribution (no extends)")

    # srcext: source_rebuild
    dist_srcext = get_distribution_file(index, 'srcext')
    assert dist_srcext.extends is not None, "srcext must have 'extends'"
    assert dist_srcext.extends[0]['distro_name'] == 'upstream'
    assert dist_srcext.extends[0]['extension_method'] == 'source_rebuild'
    print("       -> 'srcext': verified extends 'upstream' with method 'source_rebuild'")

    # binext: binary_import
    dist_binext = get_distribution_file(index, 'binext')
    assert dist_binext.extends is not None, "binext must have 'extends'"
    assert dist_binext.extends[0]['distro_name'] == 'upstream'
    assert dist_binext.extends[0]['extension_method'] == 'binary_import'
    print("       -> 'binext': verified extends 'upstream' with method 'binary_import'")


def test_cached_distribution_annotations():
    print(" [3/6] Checking distribution cache annotations (source_rebuild vs binary_import)...")
    index = rosdistro.get_index(INDEX_URL)
    
    # In srcext (source_rebuild), upstream repos are adopted under srcext's name
    cache_srcext = rosdistro.get_cached_distribution(index, 'srcext')
    repo_downstream = cache_srcext.repositories['downstream_src_a']
    assert repo_downstream.origin_distro == 'srcext'
    print("       -> 'downstream_src_a' origin_distro is 'srcext'")

    repo_upstream_c_src = cache_srcext.repositories['upstream_c']
    assert repo_upstream_c_src.origin_distro == 'srcext'
    print("       -> 'upstream_c' in srcext: origin_distro adopted as 'srcext' (rebuilt under srcext)")

    # In binext (binary_import), upstream repos retain origin_distro='upstream' & extension_method='binary_import'
    cache_binext = rosdistro.get_cached_distribution(index, 'binext')
    repo_upstream_c_bin = cache_binext.repositories['upstream_c']
    assert repo_upstream_c_bin.origin_distro == 'upstream'
    assert repo_upstream_c_bin.extension_method == 'binary_import'
    print("       -> 'upstream_c' in binext: origin_distro='upstream' & extension_method='binary_import'")

    repo_downstream_bin = cache_binext.repositories['downstream_bin_a']
    assert repo_downstream_bin.origin_distro == 'binext'
    print("       -> 'downstream_bin_a' origin_distro is 'binext'")


def test_edge_case_binary_import_override_forbidden():
    print(" [4/6] Checking Edge Case 1: Disallowing package override in binary_import...")
    base_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['resolute']},
        'repositories': {
            'common_pkg': {
                'release': {
                    'packages': ['common_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/ros-gbp/core-release.git',
                    'version': '1.0.0'
                }
            }
        }
    }
    child_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['resolute']},
        'extends': [{'distro_name': 'base', 'extension_method': 'binary_import'}],
        'repositories': {
            'common_pkg': {
                'release': {
                    'packages': ['common_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/ros-gbp/core-release.git',
                    'version': '2.0.0'
                }
            }
        }
    }
    base_dist = DistributionFile('base', base_data)
    child_dist = DistributionFile('child', child_data)
    
    error_caught = False
    try:
        child_dist.merge_extends(base_dist, 'binary_import')
    except RuntimeError as e:
        if "violates ABI compatibility" in str(e):
            error_caught = True
            print(f"       -> Expected error caught: {e}")
    
    assert error_caught, "Failed to forbid package override in binary_import!"


def test_edge_case_source_rebuild_override_allowed():
    print(" [5/6] Checking Edge Case 2: Allowing package override in source_rebuild...")
    base_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['resolute']},
        'repositories': {
            'common_pkg': {
                'source': {'type': 'git', 'url': 'https://github.com/base/common.git', 'version': 'main'},
                'release': {
                    'packages': ['common_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/base-release/common-release.git',
                    'version': '1.0.0'
                }
            }
        }
    }
    child_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['resolute']},
        'extends': [{'distro_name': 'base', 'extension_method': 'source_rebuild'}],
        'repositories': {
            'common_pkg': {
                'release': {
                    'packages': ['common_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/child-release/common-release.git',
                    'version': '2.0.0'
                }
            }
        }
    }
    base_dist = DistributionFile('base', base_data)
    child_dist = DistributionFile('child', child_data)
    # Merging under source_rebuild must succeed and keep child's release version
    child_dist.merge_extends(base_dist, 'source_rebuild')
    assert child_dist.repositories['common_pkg'].release_repository.version == '2.0.0'
    # Parent's source repository is inherited because child did not specify one
    assert child_dist.repositories['common_pkg'].source_repository.url == 'https://github.com/base/common.git'
    print("       -> Allowed! Child overridden version 2.0.0 preserved and parent source repo merged.")


def test_edge_case_multi_parent_collision_warning():
    print(" [6/6] Checking Edge Case 3: Multi-parent collision resolution (first-parent wins)...")
    parent_a = DistributionFile('parent_a', {
        'type': 'distribution', 'version': 3, 'release_platforms': {'ubuntu': ['resolute']},
        'repositories': {'shared_repo': {'release': {'packages': ['shared_pkg'], 'tags': {'release': 'release/{package}/{version}'}, 'url': 'https://github.com/a.git', 'version': '1.0.0'}}}
    })
    parent_b = DistributionFile('parent_b', {
        'type': 'distribution', 'version': 3, 'release_platforms': {'ubuntu': ['resolute']},
        'repositories': {'shared_repo': {'release': {'packages': ['shared_pkg'], 'tags': {'release': 'release/{package}/{version}'}, 'url': 'https://github.com/b.git', 'version': '2.0.0'}}}
    })
    child = DistributionFile('child', {
        'type': 'distribution', 'version': 3, 'release_platforms': {'ubuntu': ['resolute']},
        'extends': [{'distro_name': 'parent_a', 'extension_method': 'source_rebuild'}, {'distro_name': 'parent_b', 'extension_method': 'source_rebuild'}],
        'repositories': {}
    })
    
    # Merge parent_a first, then parent_b
    child.merge_extends(parent_a, 'source_rebuild')
    child.merge_extends(parent_b, 'source_rebuild')
    
    # Precedence: parent_a was merged first, so version 1.0.0 from parent_a must be retained
    assert child.repositories['shared_repo'].release_repository.version == '1.0.0'
    print("       -> Collision resolved! First parent ('parent_a', v1.0.0) took precedence over 'parent_b'.")


def main():
    print("=" * 70)
    print(" VALIDATING ROSDISTRO FORK & EDGE CASES (REP-159)")
    print(f" Index: {INDEX_PATH}")
    print("=" * 70)
    try:
        test_format_3_parsing()
        test_extension_definitions()
        test_cached_distribution_annotations()
        test_edge_case_binary_import_override_forbidden()
        test_edge_case_source_rebuild_override_allowed()
        test_edge_case_multi_parent_collision_warning()
        print("\n[SUCCESS] All rosdistro local checks & edge cases PASSED!\n")
        return 0
    except Exception as e:
        print(f"\n[FAILURE] Validation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
