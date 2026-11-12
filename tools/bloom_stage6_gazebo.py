#!/usr/bin/env python3
# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""
Bloom Debian release generator for Stage 6 (extendablejetty / extendablelyrical)
using submodules/bloom (feat/rep159-workspace-package) and submodules/rosdistro
(feat/rep159-workspace-package).

Hosts isolated GBP branches (release/<distro>/<pkg>, debian/<distro>/resolute/<pkg>)
and tags in KmoM88/rep159-testing.git so zero collaborator release repositories
are touched.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if sys.prefix == sys.base_prefix:
    venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python3")
    if os.path.isfile(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)

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

STEP1_PACKAGES = [
    {
        "distro": "extendablejetty",
        "name": "ros_workspace_shell",
        "version": "0.1.0",
        "inc": "1",
        "url": "https://github.com/rep159-testing/ros_workspace_shell.git",
        "ref": "0.1.0",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-cmake",
        "version": "5.1.1",
        "inc": "1",
        "url": "https://github.com/gazebosim/gz-cmake.git",
        "ref": "gz-cmake5_5.1.1",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-utils",
        "version": "4.0.0",
        "inc": "1",
        "url": "https://github.com/gazebosim/gz-utils.git",
        "ref": "gz-utils4_4.0.0",
        "patch_gz_cmake_export": True,
    },
    {
        "distro": "extendablejetty",
        "name": "gz-math",
        "version": "9.3.0",
        "inc": "1",
        "url": "https://github.com/gazebosim/gz-math.git",
        "ref": "gz-math9_9.3.0",
        "patch_gz_cmake_export": True,
    },
    {
        "distro": "extendablelyrical",
        "name": "ros_workspace_shell",
        "version": "0.1.0",
        "inc": "1",
        "url": "https://github.com/rep159-testing/ros_workspace_shell.git",
        "ref": "0.1.0",
        "patch_gz_cmake_export": False,
    },
    {
        "distro": "extendablelyrical",
        "name": "gz-demo-math",
        "version": "1.0.1",
        "inc": "1",
        "url": "https://github.com/j-rivero/gz-demo-math.git",
        "ref": "gz-demo-math_1.0.1",
        "patch_gz_cmake_export": False,
    },
]


def load_rosdep_map():
    rosdep_map = {}
    for url in [
        "https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/base.yaml",
        "https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/python.yaml",
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
        run(["git", "remote", "add", "target", REPO_ROOT], cwd=work_repo)

        refs_to_push = []
        for item in packages:
            distro = item["distro"]
            pkg_name = item["name"]
            ver = item["version"]
            inc = item["inc"]
            full_ver = f"{ver}-{inc}"

            print(f"\n=== Blooming {pkg_name} {full_ver} for {distro} ===")
            src_clone = os.path.join(tmpdir, f"src_{distro}_{pkg_name}")
            run(["git", "clone", "--branch", item["ref"], "--depth", "1", item["url"], src_clone])

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

            for entry in os.listdir(src_clone):
                if entry == ".git":
                    continue
                src_path = os.path.join(src_clone, entry)
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

            run(["git", "add", "-A"], cwd=work_repo)
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

            run(["git", "add", "debian"], cwd=work_repo)
            run(
                ["git", "commit", "-m", f"Generated debian files for resolute ({subs['Package']} {full_ver})"],
                cwd=work_repo,
            )
            run(["git", "tag", "-f", "-a", deb_tag, "-m", f"Debian release {deb_tag}"], cwd=work_repo)

            refs_to_push.extend(
                [
                    f"refs/heads/{rel_branch}:refs/heads/{rel_branch}",
                    f"refs/tags/{rel_tag}:refs/tags/{rel_tag}",
                    f"refs/heads/{deb_branch}:refs/heads/{deb_branch}",
                    f"refs/tags/{deb_tag}:refs/tags/{deb_tag}",
                ]
            )

        print("\nPushing branches and tags to local root repository...")
        run(["git", "push", "-f", "target"] + refs_to_push, cwd=work_repo)
        if push_remote:
            print("Pushing branches and tags to origin (KmoM88/rep159-testing.git)...")
            run(["git", "push", "-f", "origin"] + refs_to_push, cwd=REPO_ROOT)


def main():
    parser = argparse.ArgumentParser(description="Bloom Stage 6 Gazebo packages")
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push generated GBP branches and tags to origin (KmoM88/rep159-testing.git)",
    )
    args = parser.parse_args()
    bloom_packages(STEP1_PACKAGES, push_remote=args.push)


if __name__ == "__main__":
    main()
