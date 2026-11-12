#!/usr/bin/env python3
# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""
Unified stage configuration, branch checkout, job generation, and Jenkins
pipeline runner for REP-159 validation stages (Stages 1 through 6) on
https://build.test.ros2.org.

All stage pipelines strictly use the isolated 'extendable*' ('E*') namespace
and never modify or trigger collaborator ('U*', 'S*', 'B*', 'G*', 'D*', 'C*')
branches, distributions, or Jenkins jobs.
"""

import argparse
import os
import re
import subprocess
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Auto-reexec inside repo's virtual environment if not already in a venv
if sys.prefix == sys.base_prefix:
    venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python3")
    if os.path.isfile(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)

for submodule, subdir in [
    ("ros_buildfarm", ""),
    ("rosdistro", "src"),
    ("rosdep", "src"),
    ("bloom", ""),
]:
    submodule_path = os.path.join(REPO_ROOT, "submodules", submodule, subdir).rstrip("/")
    if os.path.isdir(submodule_path) and submodule_path not in sys.path:
        sys.path.insert(0, submodule_path)

DEFAULT_JENKINS_URL = os.environ.get("JENKINS_URL", "https://build.test.ros2.org")

STAGES = {
    "stage1": {
        "description": "Stage 1: Regex Binary Renaming Engine (binary_rule) in extendable (E*)",
        "branches": {
            "rosdistro": "feature/rep159-binary-naming-regex",
            "rosdep": "feat/rep159-binary-lookup",
            "ros_buildfarm": "feat/rep159-binary-naming",
            "reprepro-updater": "feat/package-prefix",
            "rep159-rosdistro": "feat/extendable-binary-naming",
            "ros_buildfarm_config": "feat/extendable-binary-naming",
            "reps": "feature/rep-159-binary-name-templating",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/extendable-binary-naming/index-rep159.yaml",
        "release_builds": [("extendable", "release")],
        "ci_distros": ["extendable"],
        "waves": [
            [
                "Esrc_uR__upstream_a__ubuntu_resolute__source",
                "Esrc_uR__upstream_b__ubuntu_resolute__source",
                "Esrc_uR__upstream_c__ubuntu_resolute__source",
            ],
            ["Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary"],
            ["Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary"],
            ["Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary"],
            [
                "Erel_sync-packages-to-testing_resolute_amd64",
                "Eci__nightly-release_ubuntu_resolute_amd64",
                "Eci__source-branches_ubuntu_resolute_amd64",
                "Eci__release-branches_ubuntu_resolute_amd64",
            ],
        ],
    },
    "stage2": {
        "description": "Stage 2: Dynamic Installation Prefixes & Underlays (install_rule) in extendable/extendablebin (E*)",
        "branches": {
            "rosdistro": "feat/rep159-install-rule",
            "rosdep": "feat/rep159-binary-lookup",
            "ros_buildfarm": "feat/rep159-underlays",
            "reprepro-updater": "feat/package-prefix",
            "rep159-rosdistro": "feat/extendable-install-rule",
            "ros_buildfarm_config": "feat/extendable-install-rule",
            "reps": "feature/rep-159-install-rule",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/extendable-install-rule/index-rep159.yaml",
        "release_builds": [("extendable", "release")],
        "ci_distros": ["extendablesrc", "extendablebin"],
        "waves": [
            [
                "Esrc_uR__upstream_a__ubuntu_resolute__source",
                "Esrc_uR__upstream_b__ubuntu_resolute__source",
                "Esrc_uR__upstream_c__ubuntu_resolute__source",
            ],
            ["Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary"],
            ["Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary"],
            ["Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary"],
            ["Erel_sync-packages-to-testing_resolute_amd64"],
            [
                "Eci__source-rebuild_ubuntu_resolute_amd64",
                "Eci__binary-import_ubuntu_resolute_amd64",
            ],
        ],
    },
    "stage3-option-a": {
        "description": "Stage 3 Option A: 3-Tier source_rebuild Chain (extendable -> extendablesrc -> extendablechain)",
        "branches": {
            "rosdistro": "feat/rep159-install-rule",
            "rosdep": "feat/rep159-binary-lookup",
            "ros_buildfarm": "feat/rep159-workspace-walk",
            "rep159-rosdistro": "feat/chained-extensions",
            "ros_buildfarm_config": "feat/chained-extensions",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/chained-extensions/index-rep159.yaml",
        "release_builds": [],
        "ci_distros": ["extendablechain"],
        "waves": [
            ["Eci__chained-import_ubuntu_resolute_amd64"],
        ],
    },
    "stage3-option-b": {
        "description": "Stage 3 Option B: 3-Tier binary_import Chain (extendable -> extendablebin -> extendablechain)",
        "branches": {
            "rosdistro": "feat/rep159-install-rule",
            "rosdep": "feat/rep159-binary-lookup",
            "ros_buildfarm": "feat/rep159-underlays",
            "rep159-rosdistro": "feat/binary-chained",
            "ros_buildfarm_config": "feat/binary-chained",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/binary-chained/index-rep159.yaml",
        "release_builds": [("extendablebin", "release")],
        "ci_distros": ["extendablechain"],
        "waves": [
            ["Esrc_uR__downstream_bin_a__ubuntu_resolute__source"],
            ["Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary"],
            ["Erel_sync-packages-to-testing_resolute_amd64"],
            ["Eci__chained-import_ubuntu_resolute_amd64"],
        ],
    },
    "stage3-mixed": {
        "description": "Stage 3 Topology 2: Hybrid Binary + Source Chain (extendablemixed)",
        "branches": {
            "rosdistro": "feat/rep159-install-rule",
            "rosdep": "feat/rep159-binary-lookup",
            "ros_buildfarm": "feat/rep159-underlays",
            "rep159-rosdistro": "feat/mixed-extensions",
            "ros_buildfarm_config": "feat/mixed-extensions",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/mixed-extensions/index-rep159.yaml",
        "release_builds": [],
        "ci_distros": ["extendablemixed"],
        "waves": [
            ["Eci__mixed-chain_ubuntu_resolute_amd64"],
        ],
    },
    "stage3-diamond": {
        "description": "Stage 3 Topology 3: Multi-Parent Diamond DAG (extendablediamond)",
        "branches": {
            "rosdistro": "feat/rep159-install-rule",
            "rosdep": "feat/rep159-binary-lookup",
            "ros_buildfarm": "feat/rep159-underlays",
            "rep159-rosdistro": "feat/diamond-extensions",
            "ros_buildfarm_config": "feat/diamond-extensions",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/diamond-extensions/index-rep159.yaml",
        "release_builds": [],
        "ci_distros": ["extendablediamond"],
        "waves": [
            ["Eci__diamond-chain_ubuntu_resolute_amd64"],
        ],
    },
    "stage4": {
        "description": "Stage 4 & 5: Full ros_workspace + ament_cmake Chaining, Bloom & Cache Lifecycle in extendable/extendablebin (E*)",
        "branches": {
            "rosdistro": "feat/rep159-install-rule",
            "rosdep": "feat/rep159-binary-lookup",
            "bloom": "feat/rep159-rules-support",
            "ros_workspace": "feat/rep159-parent-chaining",
            "ros_buildfarm": "feat/extendable-workspace",
            "rep159-rosdistro": "feat/extendable-workspace",
            "ros_buildfarm_config": "feat/extendable-workspace",
            "reps": "feature/rep-159-install-rule",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/extendable-workspace/index-rep159.yaml",
        "release_builds": [
            ("extendable", "release"),
            ("extendablebin", "extbin"),
        ],
        "ci_distros": ["extendable", "extendablebin"],
        "waves": [
            [
                "extendable_rosdistro-cache",
                "extendablebin_rosdistro-cache",
                "Esrc_uR__ament_package__ubuntu_resolute__source",
                "Esrc_uR__ament_cmake_core__ubuntu_resolute__source",
                "Esrc_uR__ros_workspace__ubuntu_resolute__source",
                "Esrc_uR__extbin_ros_workspace__ubuntu_resolute__source",
                "Esrc_uR__extbin_downstream_bin_a__ubuntu_resolute__source",
            ],
            ["Ebin_uR64__ament_package__ubuntu_resolute_amd64__binary"],
            ["Ebin_uR64__ament_cmake_core__ubuntu_resolute_amd64__binary"],
            [
                "Ebin_uR64__ros_workspace__ubuntu_resolute_amd64__binary",
                "Ebin_uR64__extbin_ros_workspace__ubuntu_resolute_amd64__binary",
            ],
            [
                "Erel_sync-packages-to-testing_resolute_amd64",
                "Ebin_uR64__extbin_downstream_bin_a__ubuntu_resolute_amd64__binary",
            ],
            [
                "Erel_extbin_sync-packages-to-testing_resolute_amd64",
                "Eci__workspace-release_ubuntu_resolute_amd64",
            ],
            [
                "Eci__workspace-binary-import_ubuntu_resolute_amd64",
            ],
        ],
    },
    "stage6-gazebo-step1": {
        "description": "Stage 6 Step 6B-1 & 6D: Adopted workspace_package (ros_workspace_shell) + Gazebo Jetty -> Lyrical (gz-demo-math) & rosdistro-reviewer EOL check",
        "branches": {
            "rosdistro": "feat/rep159-workspace-package",
            "rosdep": "feat/rep159-binary-lookup",
            "bloom": "feat/rep159-workspace-package",
            "ros_workspace": "feat/rep159-parent-chaining",
            "ros_workspace_shell": "main",
            "ros_buildfarm": "feat/extendable-workspace-package",
            "rep159-rosdistro": "feat/extendable-gazebo",
            "ros_buildfarm_config": "feat/extendable-gazebo",
            "reps": "feature/rep-159-workspace-package",
            "rosdistro-reviewer": "feat/rep159-eol-date",
        },
        "config_url": "https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/feat/extendable-gazebo/index-rep159.yaml",
        "release_builds": [
            ("extendablejetty", "extjetty"),
            ("extendablelyrical", "extlyrical"),
        ],
        "ci_distros": [
            "extendablejetty",
            "extendablelyricalsrc",
            "extendablelyrical",
        ],
        "waves": [
            [
                "Esrc_uR__extjetty_ros_workspace_shell__ubuntu_resolute__source",
                "Esrc_uR__extjetty_gz-cmake__ubuntu_resolute__source",
                "Esrc_uR__extjetty_gz-utils__ubuntu_resolute__source",
                "Esrc_uR__extjetty_gz-math__ubuntu_resolute__source",
                "Esrc_uR__extlyrical_ros_workspace_shell__ubuntu_resolute__source",
                "Esrc_uR__extlyrical_gz-demo-math__ubuntu_resolute__source",
            ],
            ["Ebin_uR64__extjetty_ros_workspace_shell__ubuntu_resolute_amd64__binary"],
            [
                "Ebin_uR64__extjetty_gz-cmake__ubuntu_resolute_amd64__binary",
                "Ebin_uR64__extlyrical_ros_workspace_shell__ubuntu_resolute_amd64__binary",
            ],
            ["Ebin_uR64__extjetty_gz-utils__ubuntu_resolute_amd64__binary"],
            ["Ebin_uR64__extjetty_gz-math__ubuntu_resolute_amd64__binary"],
            [
                "Erel_extjetty_sync-packages-to-testing_resolute_amd64",
                "Ebin_uR64__extlyrical_gz-demo-math__ubuntu_resolute_amd64__binary",
            ],
            [
                "Erel_extlyrical_sync-packages-to-testing_resolute_amd64",
                "Eci__gazebo-jetty-release_ubuntu_resolute_amd64",
                "Eci__gazebo-lyrical-source-rebuild_ubuntu_resolute_amd64",
                "Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64",
            ],
        ],
    },
}


def list_stages():
    print("Available REP-159 Validation Stages:")
    print("=" * 88)
    for name, info in STAGES.items():
        print(f"[{name}]")
        print(f"  Description: {info['description']}")
        print(f"  Config URL:  {info['config_url']}")
        print("  Branches:")
        for sub, br in info["branches"].items():
            print(f"    - submodules/{sub:<24} -> {br}")
        total_jobs = sum(len(w) for w in info["waves"])
        print(f"  Jenkins Pipeline: {len(info['waves'])} wave(s), {total_jobs} job(s)")
        print("-" * 88)


def checkout_stage_branches(stage_name, verify_only=False):
    info = STAGES[stage_name]
    action = "Verifying" if verify_only else "Checking out"
    print(f"=== {action} submodule branches for '{stage_name}' ===")
    all_ok = True
    for sub, target_branch in info["branches"].items():
        sub_dir = os.path.join(REPO_ROOT, "submodules", sub)
        if not os.path.isdir(sub_dir):
            print(f"  [ERROR] Submodule directory missing: {sub_dir}", file=sys.stderr)
            all_ok = False
            continue
        if not verify_only:
            subprocess.run(
                ["git", "-C", sub_dir, "checkout", target_branch],
                check=True,
            )
        cur_branch = subprocess.check_output(
            ["git", "-C", sub_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
        ).strip()
        cur_sha = subprocess.check_output(
            ["git", "-C", sub_dir, "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
        match_str = "OK" if cur_branch == target_branch else f"MISMATCH (expected {target_branch})"
        if cur_branch != target_branch:
            all_ok = False
        print(f"  - submodules/{sub:<24} : {cur_branch} ({cur_sha}) [{match_str}]")
    if not all_ok:
        sys.exit(1)


def generate_stage_jobs(stage_name, dry_run=False):
    info = STAGES[stage_name]
    config_url = info["config_url"]
    rb_dir = os.path.join(REPO_ROOT, "submodules", "ros_buildfarm")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{rb_dir}:{os.path.join(REPO_ROOT, 'submodules', 'rosdistro', 'src')}"

    print(f"=== Generating Jenkins Jobs for '{stage_name}' (dry_run={dry_run}) ===")
    for distro_name, release_build_name in info["release_builds"]:
        cmd = [
            sys.executable,
            "scripts/release/generate_release_script.py",
            config_url,
            distro_name,
            release_build_name,
            "ubuntu",
            "resolute",
            "amd64",
        ]
        if not dry_run:
            cmd.append("--commit")
        print(f"[RELEASE GEN] {' '.join(cmd)}", flush=True)
        subprocess.run(cmd, cwd=rb_dir, env=env, check=True)

    for distro_name in info["ci_distros"]:
        cmd = [
            sys.executable,
            "scripts/ci/generate_ci_jobs.py",
            config_url,
            distro_name,
        ]
        if dry_run:
            cmd.append("--dry-run")
        print(f"[CI GEN] {' '.join(cmd)}", flush=True)
        subprocess.run(cmd, cwd=rb_dir, env=env, check=True)


def set_priority_1(jenkins, job_name):
    job = jenkins.get_job(job_name)
    cfg = job.get_config()
    new_cfg = re.sub(r"<priority>\d+</priority>", "<priority>1</priority>", cfg)
    if new_cfg != cfg:
        job.update_config(new_cfg)
        print(f"[PRIORITY] Set priority=1 on {job_name}", flush=True)


def get_last_num(job):
    try:
        return job.get_last_buildnumber()
    except Exception:
        return 0


def wait_for_import_idle(jenkins):
    time.sleep(5)
    for _ in range(60):
        try:
            imp = jenkins.get_job("Erel_import-package")
            if not imp.is_queued() and not imp.is_running():
                return
        except Exception:
            pass
        time.sleep(5)


def trigger_if_needed(jenkins, name):
    job = jenkins.get_job(name)
    base = get_last_num(job)
    if job.is_running():
        print(f"[RUNNING] {name} currently running build #{base}", flush=True)
        return base - 1
    if not job.is_queued():
        job.invoke()
        print(f"[TRIGGER] Invoked {name} (prev #{base})", flush=True)
    else:
        print(f"[QUEUED] {name} already queued (prev #{base})", flush=True)
    return base


def wait_for_jobs(jenkins, baselines, poll_interval=15):
    results = {}
    pending = dict(baselines)
    while pending:
        for name, base in list(pending.items()):
            try:
                job = jenkins.get_job(name)
                num = get_last_num(job)
                if num > base:
                    build = job.get_build(num)
                    if not build.is_running():
                        status = build.get_status()
                        results[name] = (num, status)
                        print(f"[DONE] {name} #{num} -> {status}", flush=True)
                        del pending[name]
            except Exception as exc:
                print(f"[WARN] {name}: {exc}", flush=True)
        if pending:
            time.sleep(poll_interval)
    return results


def show_stage_status(stage_name, jenkins_url=DEFAULT_JENKINS_URL):
    from ros_buildfarm.jenkins import connect

    info = STAGES[stage_name]
    jenkins = connect(jenkins_url)
    print(f"=== Jenkins Job Status for '{stage_name}' on {jenkins_url} ===")
    for wave_idx, wave in enumerate(info["waves"], 1):
        print(f"Wave {wave_idx}:")
        for job_name in wave:
            try:
                job = jenkins.get_job(job_name)
                num = get_last_num(job)
                queued = job.is_queued()
                running = job.is_running()
                status = "NO_BUILDS"
                if num > 0:
                    build = job.get_build(num)
                    status = build.get_status() or ("RUNNING" if build.is_running() else "UNKNOWN")
                extra = " [QUEUED]" if queued else (" [RUNNING]" if running else "")
                print(f"  - {job_name:<62} #{num:<4} {status}{extra}")
            except Exception as exc:
                print(f"  - {job_name:<62} [ERROR: {exc}]")


def run_stage_pipeline(stage_name, jenkins_url=DEFAULT_JENKINS_URL, prioritize=True):
    from ros_buildfarm.jenkins import connect

    info = STAGES[stage_name]
    jenkins = connect(jenkins_url)
    all_jobs = [j for wave in info["waves"] for j in wave]
    if prioritize:
        for job_name in all_jobs:
            set_priority_1(jenkins, job_name)

    all_results = []
    for wave_idx, wave in enumerate(info["waves"], 1):
        print(f"=== Wave {wave_idx}/{len(info['waves'])}: {', '.join(wave)} ===", flush=True)
        baselines = {name: trigger_if_needed(jenkins, name) for name in wave}
        res = wait_for_jobs(jenkins, baselines)
        all_results.append(res)
        if any(name.startswith(("Esrc_", "Ebin_")) for name in wave):
            wait_for_import_idle(jenkins)
        for job_name, (build_num, status) in res.items():
            if status != "SUCCESS":
                print(
                    f"[ERROR] Wave {wave_idx} job {job_name} #{build_num} finished with {status}. Aborting.",
                    file=sys.stderr,
                    flush=True,
                )
                sys.exit(1)

    print(f"=== ALL WAVES FOR '{stage_name}' COMPLETED SUCCESSFULLY ===", flush=True)
    for res in all_results:
        for job_name, (build_num, status) in res.items():
            print(f"SUMMARY: {job_name} #{build_num} -> {status}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Manage submodule branches and Jenkins E* pipelines per REP-159 stage"
    )
    parser.add_argument(
        "--list-stages",
        action="store_true",
        help="List all defined REP-159 stages, submodule branches, and job waves",
    )
    parser.add_argument(
        "--stage",
        choices=sorted(STAGES.keys()),
        help="Target stage name",
    )
    parser.add_argument(
        "--checkout",
        action="store_true",
        help="Checkout the submodule branches defined for --stage",
    )
    parser.add_argument(
        "--verify-branches",
        action="store_true",
        help="Verify that current submodule branches match --stage",
    )
    parser.add_argument(
        "--generate-jobs",
        action="store_true",
        help="Generate Jenkins release and CI jobs for --stage on build.test.ros2.org",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run when generating jobs with --generate-jobs",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show Jenkins build status for all jobs in --stage",
    )
    parser.add_argument(
        "--run-pipeline",
        action="store_true",
        help="Trigger and orchestrate all ordered job waves for --stage on Jenkins",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_JENKINS_URL,
        help=f"Jenkins URL (default: {DEFAULT_JENKINS_URL})",
    )
    args = parser.parse_args()

    if args.list_stages or not args.stage:
        list_stages()
        if not args.stage:
            return

    if args.checkout:
        checkout_stage_branches(args.stage, verify_only=False)
    elif args.verify_branches:
        checkout_stage_branches(args.stage, verify_only=True)

    if args.generate_jobs:
        generate_stage_jobs(args.stage, dry_run=args.dry_run)

    if args.status:
        show_stage_status(args.stage, jenkins_url=args.url)

    if args.run_pipeline:
        run_stage_pipeline(args.stage, jenkins_url=args.url)


if __name__ == "__main__":
    main()
