#!/usr/bin/env python3
# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""
Inspects REP-159 CI test jobs and their historical builds on build.test.ros2.org.
Supports both anonymous queries and authenticated queries via .env / ~/.buildfarm/jenkins.ini.
"""

import datetime
import json
import os
import sys
import urllib.request
import urllib.error

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_JENKINS_URL = "https://build.test.ros2.org"

REP159_JOBS = [
    "Uci__nightly-release_ubuntu_resolute_amd64",
    "Uci__source-branches_ubuntu_resolute_amd64",
    "Uci__release-branches_ubuntu_resolute_amd64",
    "Sci__nightly-release_ubuntu_resolute_amd64",
    "Bci__nightly-release_ubuntu_resolute_amd64",
]


def load_env_credentials():
    dotenv_path = os.path.join(REPO_ROOT, ".env")
    user, token = os.environ.get("JENKINS_USER"), os.environ.get("JENKINS_TOKEN")
    if (not user or not token) and os.path.isfile(dotenv_path):
        with open(dotenv_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k == "JENKINS_USER" and not user:
                    user = v
                elif k == "JENKINS_TOKEN" and not token:
                    token = v
    return user, token


def make_request(url, username=None, password=None):
    req = urllib.request.Request(url, headers={"User-Agent": "REP159-Testing-Harness/1.0"})
    if username and password:
        import base64
        auth_bytes = f"{username}:{password}".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(auth_bytes).decode("ascii")
        req.add_header("Authorization", auth_header)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_duration(ms):
    if not ms:
        return "-"
    seconds = int(ms / 1000)
    mins, secs = divmod(seconds, 60)
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def format_timestamp(ms):
    if not ms:
        return "-"
    dt = datetime.datetime.fromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_build_cause(build_data):
    actions = build_data.get("actions", [])
    for action in actions:
        if not isinstance(action, dict):
            continue
        for cause in action.get("causes", []):
            desc = cause.get("shortDescription")
            user_name = cause.get("userName")
            user_id = cause.get("userId")
            if user_name and user_id:
                return f"{user_name} ({user_id})"
            if desc:
                return desc
    return "Timer / Automated"


def inspect_jobs(base_url=DEFAULT_JENKINS_URL):
    user, token = load_env_credentials()
    auth_str = f"authenticated as '{user}'" if (user and token) else "anonymous mode (read-only)"
    print("=" * 80)
    print(f" REP-159 BUILDFARM JOBS INSPECTION ({base_url})")
    print(f" Mode: {auth_str}")
    print("=" * 80)

    summary_rows = []

    for job_name in REP159_JOBS:
        job_api_url = f"{base_url}/job/{job_name}/api/json?tree=name,url,color,builds[number,url,result,timestamp,duration,actions[causes[shortDescription,userId,userName]]]"
        try:
            try:
                data = make_request(job_api_url, user, token)
            except urllib.error.HTTPError as e:
                if e.code == 401 and user:
                    # Fallback to anonymous read
                    data = make_request(job_api_url)
                else:
                    raise

            builds = data.get("builds", [])
            total_builds = len(builds)
            last_build = builds[0] if builds else None

            print(f"\n Job: {job_name}")
            print(f"   URL: {data.get('url', f'{base_url}/job/{job_name}')}")
            print(f"   Total Historical Builds: {total_builds}")

            if not builds:
                print("   -> No builds executed yet.")
                summary_rows.append((job_name, 0, "-", "-", "-", "-"))
                continue

            last_res = last_build.get("result", "IN_PROGRESS")
            last_cause = get_build_cause(last_build)
            last_date = format_timestamp(last_build.get("timestamp"))
            summary_rows.append((job_name, total_builds, f"#{last_build['number']}", last_res, last_cause, last_date))

            print("   Execution History (most recent first):")
            for b in builds:
                num = b.get("number")
                res = b.get("result", "RUNNING")
                ts = format_timestamp(b.get("timestamp"))
                dur = format_duration(b.get("duration"))
                cause = get_build_cause(b)
                console_url = f"{b.get('url')}console"
                print(f"     • Build #{num:<3} [{res:<7}] Date: {ts} | Duration: {dur:<7} | Trigger: {cause}")
                print(f"       Console: {console_url}")

        except Exception as e:
            print(f"\n Job: {job_name} [ERROR: {e}]")
            summary_rows.append((job_name, "-", "-", "ERROR", str(e), "-"))

    print("\n" + "=" * 80)
    print(" SUMMARY MATRIX:")
    print("=" * 80)
    print(f" {'Job Name':<44} {'Total':<6} {'Last':<6} {'Status':<8} {'Triggered By':<22}")
    print("-" * 80)
    for name, total, last_num, status, cause, _ in summary_rows:
        short_name = name.split("__")[0] + "__" + name.split("__")[1][:25]
        print(f" {name:<44} {str(total):<6} {last_num:<6} {status:<8} {cause[:22]:<22}")
    print("=" * 80)


if __name__ == "__main__":
    inspect_jobs()
