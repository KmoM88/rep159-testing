#!/usr/bin/env python3
# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""
CLI tool to inspect and trigger REP-159 CI jobs on Jenkins (build.test.ros2.org).
Supports credentials from ~/.buildfarm/jenkins.ini or environment variables:
  - JENKINS_USER
  - JENKINS_TOKEN
"""

import argparse
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Auto-reexec inside repo's virtual environment if not already in a venv
if sys.prefix == sys.base_prefix:
    venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python")
    if os.path.isfile(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)

for submodule in ["ros_buildfarm", "rosdistro", "rosdep"]:
    submodule_path = os.path.join(REPO_ROOT, "submodules", submodule)
    if os.path.isdir(submodule_path) and submodule_path not in sys.path:
        sys.path.insert(0, submodule_path)

# Automatically load .env if present
dotenv_path = os.path.join(REPO_ROOT, ".env")
if os.path.isfile(dotenv_path):
    with open(dotenv_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and v and k not in os.environ:
                os.environ[k] = v

try:
    from jenkinsapi.jenkins import Jenkins
    from jenkinsapi.utils.crumb_requester import CrumbRequester
except ImportError:
    print("Error: 'jenkinsapi' is required. Install with: pip install jenkinsapi", file=sys.stderr)
    sys.exit(1)

from ros_buildfarm.jenkins_credentials import get_credentials

DEFAULT_JENKINS_URL = os.environ.get("JENKINS_URL", "http://192.168.30.206:8080")
REP159_JOBS = [
    # Upstream hierarchy
    "Uci__nightly-release_ubuntu_resolute_amd64",
    "Uci__source-branches_ubuntu_resolute_amd64",
    "Uci__release-branches_ubuntu_resolute_amd64",
    "Sci__nightly-release_ubuntu_resolute_amd64",
    "Bci__nightly-release_ubuntu_resolute_amd64",
    # Extendable isolated hierarchy
    "Eci__nightly-release_ubuntu_resolute_amd64",
    "Eci__source-branches_ubuntu_resolute_amd64",
    "Eci__release-branches_ubuntu_resolute_amd64",
    "Eci__source-rebuild_ubuntu_resolute_amd64",
    "Eci__binary-import_ubuntu_resolute_amd64",
    "Eci__chained-import_ubuntu_resolute_amd64",
    "Eci__mixed-chain_ubuntu_resolute_amd64",
    "Eci__diamond-chain_ubuntu_resolute_amd64",
    # Composable hierarchy
    "Cci__nightly-release_ubuntu_resolute_amd64",
]


def resolve_auth(jenkins_url):
    ini_user, ini_pass = None, None
    try:
        ini_user, ini_pass = get_credentials(jenkins_url)
    except Exception:
        pass
    if ini_user and ini_pass:
        return ini_user, ini_pass

    if "build.test.ros2.org" in jenkins_url:
        username = os.environ.get("TEST_BUILDFARM_USER") or os.environ.get("JENKINS_USER", "kmom88")
        password = os.environ.get("TEST_BUILDFARM_TOKEN") or os.environ.get("JENKINS_TOKEN")
        return username, password

    username = os.environ.get("JENKINS_USER")
    password = os.environ.get("JENKINS_TOKEN")
    return username, password


def get_jenkins_client(jenkins_url, username, password):
    requester = CrumbRequester(
        username=username,
        password=password,
        baseurl=jenkins_url,
        timeout=60,
    )
    return Jenkins(
        jenkins_url,
        username=username,
        password=password,
        requester=requester,
        lazy=True,
        timeout=60,
    )


def list_jobs(client):
    print(f"\nREP-159 CI Jobs on {client.baseurl}:")
    print("=" * 70)
    for job_name in REP159_JOBS:
        try:
            job = client.get_job(job_name)
            try:
                last_build = job.get_last_build()
                status = last_build.get_status() if last_build else "NO_BUILDS"
                last_num = last_build.buildno if last_build else "-"
            except Exception:
                status = "NO_BUILDS"
                last_num = "-"
            print(f" • {job_name:<45} [Last: #{last_num} - {status}]")
        except Exception as e:
            print(f" • {job_name:<45} [Not Found / Error: {e}]")
    print("=" * 70)


def trigger_job(client, job_name, watch=False):
    if job_name not in client:
        print(f"Error: Job '{job_name}' not found on {client.baseurl}", file=sys.stderr)
        sys.exit(1)

    job = client.get_job(job_name)
    print(f"Triggering build for: {job_name} ...")
    queue_item = job.invoke()
    print(f"Job successfully queued! Queue ID: {queue_item.queue_id}")

    if watch:
        print("Waiting for build to leave queue and start execution...")
        build = queue_item.block_until_building()
        print(f"Build started: #{build.buildno} ({build.baseurl})")
        print(f"Console Output: {build.baseurl}console")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and trigger REP-159 CI test jobs on Jenkins"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_JENKINS_URL,
        help=f"Jenkins base URL (default: {DEFAULT_JENKINS_URL})",
    )
    parser.add_argument(
        "--job",
        help="Specific job name to trigger",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List status of all REP-159 test jobs",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch build until it starts execution",
    )

    args = parser.parse_args()

    username, password = resolve_auth(args.url)
    if not username or not password:
        print(
            f"Error: Jenkins credentials not found for {args.url}.\n"
            "Provide them in .env, ~/.buildfarm/jenkins.ini, or set JENKINS_USER and JENKINS_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Connecting to Jenkins ({args.url}) as user '{username}'...")
    client = get_jenkins_client(args.url, username, password)

    if args.list or not args.job:
        list_jobs(client)
        if not args.job:
            print("\nTip: Specify --job <JOB_NAME> to trigger a build.")
            return

    if args.job:
        trigger_job(client, args.job, watch=args.watch)


if __name__ == "__main__":
    main()
