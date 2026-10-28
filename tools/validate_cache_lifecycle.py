#!/usr/bin/env python3
"""Validates the REP-159 cache lifecycle: unmerged on disk vs merged in memory, resolution, and invalidation."""
import os
import sys
import yaml
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'submodules', 'rosdistro', 'src'))

import rosdistro
from rosdistro import get_cached_distribution, get_index

INDEX_PATH = os.path.join(REPO_ROOT, 'submodules', 'rep159-rosdistro', 'index-v4.yaml')
INDEX_URL = f'file://{INDEX_PATH}'


def test_unmerged_on_disk_vs_merged_in_memory():
    print(" [1/3] Inspecting Cache Architecture: Unmerged on Disk vs Merged in Memory...")
    # 1. Read raw cache file on disk
    raw_cache_path = os.path.join(REPO_ROOT, 'submodules', 'rep159-rosdistro', 'binext-cache.yaml')
    with open(raw_cache_path, 'r') as f:
        disk_data = yaml.safe_load(f)
    
    disk_dist = disk_data['distribution_file'][0] if isinstance(disk_data['distribution_file'], list) else disk_data['distribution_file']
    disk_repos = list(disk_dist['repositories'].keys())
    print(f"       -> On Disk ({raw_cache_path}):")
    print(f"          Repositories stored: {disk_repos}")
    assert disk_repos == ['downstream_bin_a'], "Expected disk cache to be precleaned/unmerged (only own repos)"
    print("          * Notice: Parent packages are NOT stored in the disk cache (unmerged due to --preclean).")

    # 2. Load cached distribution via rosdistro
    index = get_index(INDEX_URL)
    mem_dist = get_cached_distribution(index, 'binext')
    mem_repos = sorted(mem_dist.repositories.keys())
    print(f"       -> In Memory (after get_cached_distribution):")
    print(f"          Repositories present: {mem_repos}")
    assert 'upstream_c' in mem_repos, "Expected parent packages to be dynamically merged into memory"
    print("          * Notice: Parent packages ('upstream_a/b/c') were dynamically resolved and merged from parent cache!")


def test_local_vs_remote_index_cache():
    print(" [2/3] Checking Local File Cache Resolution (Offline Verification)...")
    index = get_index(INDEX_URL)
    # Both upstream and child caches load purely from local file:// paths without network
    dist_upstream = get_cached_distribution(index, 'upstream')
    dist_srcext = get_cached_distribution(index, 'srcext')
    assert dist_upstream.name == 'upstream'
    assert dist_srcext.name == 'srcext'
    print("       -> Successfully resolved parent and child caches entirely offline via file://")


def test_edge_case_missing_parent_cache_failure():
    print(" [3/3] Checking Cache Invalidation / Unreachable Parent Failure...")
    # If a parent cache cannot be loaded, rosdistro MUST raise RuntimeError rather than silently failing
    fake_index = {
        'type': 'index',
        'version': 4,
        'distributions': {
            'orphan_distro': {
                'distribution': ['orphan.yaml'],
                'distribution_cache': 'orphan-cache.yaml'
            }
        }
    }
    orphan_dist = {
        'type': 'distribution',
        'version': 3,
        'extends': [{'distro_name': 'nonexistent_parent', 'extension_method': 'binary_import'}],
        'repositories': {}
    }
    orphan_cache = {
        'type': 'cache',
        'version': 2,
        'name': 'orphan_distro',
        'distribution_file': orphan_dist,
        'release_package_xmls': {}
    }
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        for fname, data in [('orphan.yaml', orphan_dist), ('orphan-cache.yaml', orphan_cache), ('index-v4.yaml', fake_index)]:
            with open(os.path.join(tmp_dir, fname), 'w') as f:
                yaml.safe_dump(data, f)
        
        tmp_index = get_index('file://' + os.path.join(tmp_dir, 'index-v4.yaml'))
        error_caught = False
        try:
            get_cached_distribution(tmp_index, 'orphan_distro')
        except RuntimeError as e:
            if "Could not load the cache of distribution 'nonexistent_parent'" in str(e):
                error_caught = True
                print(f"       -> Expected error caught: {e}")
        assert error_caught, "Failed to fail-fast on missing parent cache!"


def main():
    print("=" * 70)
    print(" VALIDATING REP-159 CACHE LIFECYCLE & RESOLUTION")
    print("=" * 70)
    try:
        test_unmerged_on_disk_vs_merged_in_memory()
        test_local_vs_remote_index_cache()
        test_edge_case_missing_parent_cache_failure()
        print("\n[SUCCESS] Cache lifecycle & edge case checks PASSED!\n")
        return 0
    except Exception as e:
        print(f"\n[FAILURE] Validation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
