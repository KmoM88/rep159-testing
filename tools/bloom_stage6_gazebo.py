#!/usr/bin/env python3
# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""
Bloom Debian release generator for Stage 6 (extendablejetty / extendablelyrical)
using submodules/bloom (feat/rep159-workspace-package) and submodules/rosdistro
(feat/rep159-workspace-package).

Pushes each package's GBP branches (release/<distro>/<pkg>, debian/<distro>/resolute/<pkg>)
and tags into its dedicated rep159-testing/<repo>-release submodule and remote.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if sys.prefix == sys.base_prefix:
    venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python3")
    if os.path.isfile(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)

import yaml  # noqa: E402

for submodule, subdir in [
    ("bloom", ""),
    ("rosdistro", "src"),
    ("rosdep", "src"),
]:
    submodule_path = os.path.join(REPO_ROOT, "submodules", submodule, subdir).rstrip("/")
    if os.path.isdir(submodule_path) and submodule_path not in sys.path:
        sys.path.insert(0, submodule_path)

ROSDISTRO_DIR = os.path.join(REPO_ROOT, "submodules", "rep159-rosdistro")
os.environ["ROSDISTRO_INDEX_URL"] = "file://" + os.path.join(ROSDISTRO_DIR, "index-v4.yaml")

import bloom.generators.common as bloom_common  # noqa: E402
import bloom.generators.debian.generator as deb_gen  # noqa: E402
from bloom.generators.debian.generator import place_template_files, process_template_files  # noqa: E402
from bloom.generators.rosdebian import RosDebianGenerator  # noqa: E402
from catkin_pkg.package import parse_package  # noqa: E402
from rosdistro import get_distribution_file, get_index  # noqa: E402

STAGE6_SINGLE_PARENT_PACKAGES = [
    {
        "distro": "extendablejetty",
        "name": "ros_workspace_shell",
        "release_submodule": "ros_workspace_shell-release",
        "version": "0.1.0",
        "inc": "1",
        "url": "https://github.com/rep159-testing/ros_workspace_shell.git",
        "ref": "feat/rep159-unset-current-prefix",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-cmake",
        "release_submodule": "gz-cmake-release",
        "version": "5.1.1",
        "inc": "1",
        "url": "https://github.com/gazebosim/gz-cmake.git",
        "ref": "gz-cmake5_5.1.1",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-utils",
        "release_submodule": "gz-utils-release",
        "version": "4.0.0",
        "inc": "1",
        "url": "https://github.com/gazebosim/gz-utils.git",
        "ref": "gz-utils4_4.0.0",
        "subdir": "",
        "patch_gz_cmake_export": True,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-math",
        "release_submodule": "gz-math-release",
        "version": "9.3.0",
        "inc": "1",
        "url": "https://github.com/gazebosim/gz-math.git",
        "ref": "gz-math9_9.3.0",
        "subdir": "",
        "patch_gz_cmake_export": True,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-tools2",
        "release_submodule": "gz-tools-release",
        "version": "2.0.4",
        "inc": "1",
        "url": "https://github.com/rep159-testing/gz-tools.git",
        "ref": "feat/rep159-jetty",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-msgs",
        "release_submodule": "gz-msgs-release",
        "version": "12.0.2",
        "inc": "1",
        "url": "https://github.com/gazebosim/gz-msgs.git",
        "ref": "gz-msgs12_12.0.2",
        "subdir": "",
        "patch_gz_cmake_export": True,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-transport",
        "release_submodule": "gz-transport-release",
        "version": "15.1.0",
        "inc": "1",
        "url": "https://github.com/rep159-testing/gz-transport.git",
        "ref": "feat/rep159-jetty",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablelyrical",
        "name": "ros_workspace_shell",
        "release_submodule": "ros_workspace_shell-release",
        "version": "0.1.0",
        "inc": "1",
        "url": "https://github.com/rep159-testing/ros_workspace_shell.git",
        "ref": "feat/rep159-unset-current-prefix",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablelyrical",
        "name": "gz-demo-math",
        "release_submodule": "gz-demo-math-release",
        "version": "1.0.1",
        "inc": "1",
        "url": "https://github.com/j-rivero/gz-demo-math.git",
        "ref": "gz-demo-math_1.0.1",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
]

STAGE6_MULTI_PARENT_EXTRA_PACKAGES = [
    {
        "distro": "extendablelyrical",
        "name": "ros_workspace",
        "release_submodule": "ros_workspace-release",
        "version": "1.0.4",
        "inc": "1",
        "url": "https://github.com/rep159-testing/ros_workspace.git",
        "ref": "feat/rep159-parent-chaining",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablelyrical",
        "name": "gz-demo-math",
        "release_submodule": "gz-demo-math-release",
        "version": "1.0.1",
        "inc": "1",
        "url": "https://github.com/j-rivero/gz-demo-math.git",
        "ref": "gz-demo-math_1.0.1",
        "subdir": "",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablelyrical",
        "name": "ros_gz_interfaces",
        "release_submodule": "ros_gz-release",
        "version": "3.0.12",
        "inc": "1",
        "url": "https://github.com/rep159-testing/ros_gz.git",
        "ref": "feat/rep159-no-vendor",
        "subdir": "ros_gz_interfaces",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablelyrical",
        "name": "ros_gz_bridge",
        "release_submodule": "ros_gz-release",
        "version": "3.0.12",
        "inc": "1",
        "url": "https://github.com/rep159-testing/ros_gz.git",
        "ref": "feat/rep159-no-vendor",
        "subdir": "ros_gz_bridge",
        "patch_gz_cmake_export": False,
    },
]


def load_rosdep_map():
    rosdep_map = {}
    for url in [
        "https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/base.yaml",
        "https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/python.yaml",
        "https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/ruby.yaml",
    ]:
        data = yaml.safe_load(urllib.request.urlopen(url).read())
        for k, v in data.items():
            if isinstance(v, dict) and "ubuntu" in v:
                u = v["ubuntu"]
                if isinstance(u, list):
                    rosdep_map[k] = u
                elif isinstance(u, dict):
                    pkgs = u.get("resolute", u.get("*", []))
                    if isinstance(pkgs, dict) and "packages" in pkgs:
                        pkgs = pkgs["packages"]
                    if isinstance(pkgs, list):
                        rosdep_map[k] = pkgs
    return rosdep_map


def make_resolver(idx, rosdep_map, rosdistro_name):
    dist_file = get_distribution_file(idx, rosdistro_name)

    def resolve_key(key, os_name, os_version, ros_distro=None, ignored=None, retry=False):
        ignored = ignored or []
        if key in ignored:
            return None, None, None
        if key in dist_file.release_packages:
            return [dist_file.get_binary_package_name(key)], "apt", "apt"
        if key in rosdep_map:
            return rosdep_map[key], "apt", "apt"
        raise RuntimeError(f"Cannot resolve rosdep key '{key}' for {rosdistro_name}")

    return resolve_key


def run(cmd, cwd=None):
    subprocess.check_call(cmd, cwd=cwd)


def bloom_packages(packages, push_remote=False):
    rosdep_map = load_rosdep_map()
    idx = get_index(os.environ["ROSDISTRO_INDEX_URL"])

    with tempfile.TemporaryDirectory() as tmpdir:
        work_repo = os.path.join(tmpdir, "work")
        os.makedirs(work_repo)
        run(["git", "init"], cwd=work_repo)
        run(["git", "config", "user.name", "Federico Rossi"], cwd=work_repo)
        run(["git", "config", "user.email", "federico.rossi@creativa77.com.ar"], cwd=work_repo)

        refs_by_submodule = {}
        for item in packages:
            distro = item["distro"]
            pkg_name = item["name"]
            rel_sub = item["release_submodule"]
            ver = item["version"]
            inc = item["inc"]
            full_ver = f"{ver}-{inc}"

            print(f"\n=== Blooming {pkg_name} {full_ver} for {distro} -> {rel_sub} ===")
            src_clone = os.path.join(tmpdir, f"src_{distro}_{pkg_name}")
            run(["git", "clone", "--branch", item["ref"], "--depth", "1", item["url"], src_clone])

            src_dir = os.path.join(src_clone, item["subdir"]) if item.get("subdir") else src_clone

            rel_branch = f"release/{distro}/{pkg_name}"
            rel_tag = f"release/{distro}/{pkg_name}/{full_ver}"

            run(["git", "checkout", "--orphan", rel_branch], cwd=work_repo)
            run(["git", "rm", "-rf", "--ignore-unmatch", "."], cwd=work_repo)
            for entry in os.listdir(work_repo):
                if entry == ".git":
                    continue
                path = os.path.join(work_repo, entry)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

            for entry in os.listdir(src_dir):
                if entry == ".git":
                    continue
                src_path = os.path.join(src_dir, entry)
                dst_path = os.path.join(work_repo, entry)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, symlinks=True)
                else:
                    shutil.copy2(src_path, dst_path)

            if item["patch_gz_cmake_export"]:
                pkg_xml_path = os.path.join(work_repo, "package.xml")
                with open(pkg_xml_path, "r") as f:
                    xml_txt = f.read()
                if "<build_export_depend>gz-cmake</build_export_depend>" not in xml_txt:
                    xml_txt = xml_txt.replace(
                        "<build_depend>gz-cmake</build_depend>",
                        "<build_depend>gz-cmake</build_depend>\n  <build_export_depend>gz-cmake</build_export_depend>",
                    )
                    with open(pkg_xml_path, "w") as f:
                        f.write(xml_txt)

            run(["git", "add", "-f", "-A"], cwd=work_repo)
            run(["git", "commit", "-m", f"Import {pkg_name} {full_ver} for {distro}"], cwd=work_repo)
            run(["git", "tag", "-f", "-a", rel_tag, "-m", f"Release {rel_tag}"], cwd=work_repo)

            deb_branch = f"debian/{distro}/resolute/{pkg_name}"
            run(["git", "checkout", "-b", deb_branch], cwd=work_repo)

            resolver = make_resolver(idx, rosdep_map, distro)
            bloom_common.resolve_rosdep_key = resolver
            deb_gen.resolve_rosdep_key = resolver

            pkg = parse_package(work_repo)
            gen = RosDebianGenerator()
            gen.rosdistro = distro
            gen.os_name = "ubuntu"
            gen.distros = ["resolute"]
            gen.debian_inc = inc
            gen.native = False
            gen.install_prefix = f"/opt/ros/{distro}"
            gen.packages = {pkg.name: pkg}

            old_cwd = os.getcwd()
            try:
                os.chdir(work_repo)
                place_template_files(".", pkg.get_build_type(), gbp=True)
                subs = gen.get_subs(pkg, "resolute", None)
                subs["release_tag"] = gen.get_release_tag(subs)
                template_files = process_template_files(".", subs)
                for tmpl in template_files:
                    if os.path.exists(tmpl):
                        os.remove(tmpl)
            finally:
                os.chdir(old_cwd)

            deb_tag = gen.generate_tag_name(subs)
            print(f"Generated Debian package: {subs['Package']}, tag: {deb_tag}")

            run(["git", "add", "-f", "debian"], cwd=work_repo)
            run(
                ["git", "commit", "-m", f"Generated debian files for resolute ({subs['Package']} {full_ver})"],
                cwd=work_repo,
            )
            run(["git", "tag", "-f", "-a", deb_tag, "-m", f"Debian release {deb_tag}"], cwd=work_repo)

            refs_by_submodule.setdefault(rel_sub, []).extend(
                [
                    f"refs/heads/{rel_branch}:refs/heads/{rel_branch}",
                    f"refs/tags/{rel_tag}:refs/tags/{rel_tag}",
                    f"refs/heads/{deb_branch}:refs/heads/{deb_branch}",
                    f"refs/tags/{deb_tag}:refs/tags/{deb_tag}",
                ]
            )

        for rel_sub, refs in refs_by_submodule.items():
            sub_dir = os.path.join(REPO_ROOT, "submodules", rel_sub)
            print(f"\nPushing branches and tags to local submodule submodules/{rel_sub}...")
            run(["git", "push", "-f", sub_dir] + refs, cwd=work_repo)
            if push_remote:
                print(f"Pushing branches and tags to origin of submodules/{rel_sub} (rep159-testing/{rel_sub}.git)...")
                run(["git", "push", "-f", "origin"] + refs, cwd=sub_dir)


def generate_lyrical_parent_subset():
    import gzip

    url = "http://repo.ros2.org/rosdistro_cache/lyrical-cache.yaml.gz"
    print(f"Fetching upstream Lyrical cache from {url} ...")
    raw = gzip.decompress(urllib.request.urlopen(url).read()).decode("utf-8")
    cache_data = yaml.safe_load(raw)

    pkg_xmls = cache_data["release_package_xmls"]
    dist_file_data = cache_data["distribution_file"]
    if isinstance(dist_file_data, list):
        dist_file_data = dist_file_data[0]
    all_repos = dist_file_data["repositories"]

    pkg_to_repo = {}
    for repo_name, rdata in all_repos.items():
        rel = rdata.get("release")
        if not rel:
            continue
        for p in rel.get("packages", [repo_name]):
            pkg_to_repo[p] = repo_name

    seed_pkgs = [
        "ament_cmake",
        "ament_cmake_gtest",
        "ament_cmake_python",
        "ament_lint_auto",
        "ament_lint_common",
        "ament_package",
        "ament_cmake_core",
        "ros_workspace",
        "rosidl_default_generators",
        "rosidl_default_runtime",
        "rosidl_pycommon",
        "rosidl_typesupport_fastrtps_c",
        "rosidl_typesupport_fastrtps_cpp",
        "builtin_interfaces",
        "std_msgs",
        "geometry_msgs",
        "rcl_interfaces",
        "actuator_msgs",
        "gps_msgs",
        "launch",
        "launch_ros",
        "launch_testing",
        "launch_testing_ament_cmake",
        "marine_acoustic_msgs",
        "nav_msgs",
        "rclcpp",
        "rclcpp_components",
        "rosgraph_msgs",
        "sensor_msgs",
        "tf2_msgs",
        "trajectory_msgs",
        "vision_msgs",
        "yaml_cpp_vendor",
    ]

    visited = set()
    queue = list(seed_pkgs)
    while queue:
        cur = queue.pop(0)
        if cur in visited or cur not in pkg_xmls:
            continue
        if cur.startswith("ros_gz") or (cur.startswith("gz_") and cur.endswith("_vendor")):
            continue
        visited.add(cur)
        pkg_obj = parse_package_string_safe(pkg_xmls[cur])
        for dep in (
            pkg_obj.build_depends
            + pkg_obj.buildtool_depends
            + pkg_obj.build_export_depends
            + pkg_obj.buildtool_export_depends
            + pkg_obj.exec_depends
            + pkg_obj.test_depends
        ):
            if dep.name in pkg_xmls and dep.name not in visited:
                queue.append(dep.name)

    selected_repos = {}
    selected_pkg_xmls = {}
    for p in sorted(visited):
        rname = pkg_to_repo[p]
        selected_pkg_xmls[p] = pkg_xmls[p]
        if rname not in selected_repos:
            orig_rel = all_repos[rname]["release"]
            selected_repos[rname] = {
                "release": {
                    "packages": [],
                    "tags": orig_rel["tags"],
                    "url": orig_rel["url"],
                    "version": orig_rel["version"],
                }
            }
        selected_repos[rname]["release"]["packages"].append(p)

    for rname, rdata in selected_repos.items():
        pkgs = sorted(rdata["release"]["packages"])
        if pkgs == [rname]:
            del rdata["release"]["packages"]
        else:
            rdata["release"]["packages"] = pkgs

    lyrical_dist = {
        "type": "distribution",
        "version": 3,
        "release_platforms": {"ubuntu": ["resolute"]},
        "install_rule": "/opt/ros/{distro}",
        "repositories": selected_repos,
    }
    lyrical_dir = os.path.join(ROSDISTRO_DIR, "lyrical")
    os.makedirs(lyrical_dir, exist_ok=True)
    with open(os.path.join(lyrical_dir, "distribution.yaml"), "w") as f:
        f.write("%YAML 1.1\n# ROS 2 Lyrical parent subset for REP-159 Stage 6 multi-parent testing.\n---\n")
        yaml.safe_dump(lyrical_dist, f, default_flow_style=False)

    lyrical_cache = {
        "type": "cache",
        "version": 2,
        "name": "lyrical",
        "distribution_file": [lyrical_dist],
        "release_package_xmls": selected_pkg_xmls,
        "source_repo_package_xmls": {},
    }
    cache_yaml_path = os.path.join(ROSDISTRO_DIR, "lyrical-cache.yaml")
    cache_gz_path = os.path.join(ROSDISTRO_DIR, "lyrical-cache.yaml.gz")
    with open(cache_yaml_path, "w") as f:
        f.write("%YAML 1.1\n# ROS distribution_cache file\n---\n")
        yaml.safe_dump(lyrical_cache, f, default_flow_style=False, width=10000)
    with open(cache_yaml_path, "rb") as f_in, gzip.GzipFile(
        filename="", mode="wb", fileobj=open(cache_gz_path, "wb"), mtime=0
    ) as f_out:
        shutil.copyfileobj(f_in, f_out)
    print(f"Generated lyrical/distribution.yaml and lyrical-cache.yaml.gz ({len(selected_pkg_xmls)} packages across {len(selected_repos)} repositories).")


def parse_package_string_safe(xml_str):
    from catkin_pkg.package import parse_package_string

    return parse_package_string(xml_str)


def main():
    parser = argparse.ArgumentParser(description="Bloom Stage 6 Gazebo packages into rep159-testing/*-release repos")
    parser.add_argument(
        "--generate-lyrical-parent",
        action="store_true",
        help="Generate lyrical/distribution.yaml and lyrical-cache.yaml.gz (156-package ROS 2 closure without ros_gz/gz_*_vendor)",
    )
    parser.add_argument(
        "--multi-parent",
        action="store_true",
        help="Also bloom ros_workspace, ros_gz_interfaces, and ros_gz_bridge for multi-parent extendablelyrical",
    )
    parser.add_argument(
        "--only-multi-parent",
        action="store_true",
        help="Bloom only ros_workspace, ros_gz_interfaces, and ros_gz_bridge for multi-parent extendablelyrical",
    )
    parser.add_argument(
        "--package",
        help="Optional package name filter to bloom only a specific package",
    )
    parser.add_argument(
        "--distro",
        help="Optional distro filter (e.g. extendablejetty, extendablelyrical)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push generated GBP branches and tags to rep159-testing/*-release.git remotes",
    )
    args = parser.parse_args()
    if args.generate_lyrical_parent:
        generate_lyrical_parent_subset()
        if not args.multi_parent and not args.only_multi_parent and not args.package and not args.push:
            return
    if args.only_multi_parent:
        pkgs = list(STAGE6_MULTI_PARENT_EXTRA_PACKAGES)
    else:
        pkgs = list(STAGE6_SINGLE_PARENT_PACKAGES)
        if args.multi_parent:
            pkgs = [p for p in pkgs if not (p["distro"] == "extendablelyrical" and p["name"] in ("ros_workspace_shell", "gz-demo-math"))]
            pkgs.extend(STAGE6_MULTI_PARENT_EXTRA_PACKAGES)
    if args.distro:
        pkgs = [p for p in pkgs if p["distro"] == args.distro]
    if args.package:
        pkgs = [p for p in pkgs if p["name"] == args.package]
    bloom_packages(pkgs, push_remote=args.push)


if __name__ == "__main__":
    main()
