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

DEFAULT_JENKINS_URL = os.environ.get("JENKINS_URL", "https://build.test.ros2.org")
REP159_JOBS = [
    # Upstream hierarchy
    "Uci__nightly-release_ubuntu_resolute_amd64",
    "Uci__source-branches_ubuntu_resolute_amd64",
    "Uci__release-branches_ubuntu_resolute_amd64",
    "Sci__nightly-release_ubuntu_resolute_amd64",
    "Bci__nightly-release_ubuntu_resolute_amd64",
    # Extendable isolated hierarchy (Stages 1-3 Release & Sync)
    "Esrc_uR__upstream_a__ubuntu_resolute__source",
    "Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary",
    "Esrc_uR__upstream_b__ubuntu_resolute__source",
    "Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary",
    "Esrc_uR__upstream_c__ubuntu_resolute__source",
    "Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary",
    "Esrc_uR__downstream_bin_a__ubuntu_resolute__source",
    "Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary",
    "Erel_import-package",
    "Erel_sync-packages-to-testing_resolute_amd64",
    "Erel_sync-packages-to-main",
    # Extendable isolated hierarchy (Stage 4 & 5 Full ros_workspace & Cache)
    "extendable_rosdistro-cache",
    "extendablebin_rosdistro-cache",
    "Esrc_uR__ament_package__ubuntu_resolute__source",
    "Ebin_uR64__ament_package__ubuntu_resolute_amd64__binary",
    "Esrc_uR__ament_cmake_core__ubuntu_resolute__source",
    "Ebin_uR64__ament_cmake_core__ubuntu_resolute_amd64__binary",
    "Esrc_uR__ros_workspace__ubuntu_resolute__source",
    "Ebin_uR64__ros_workspace__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extbin_ros_workspace__ubuntu_resolute__source",
    "Ebin_uR64__extbin_ros_workspace__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extbin_downstream_bin_a__ubuntu_resolute__source",
    "Ebin_uR64__extbin_downstream_bin_a__ubuntu_resolute_amd64__binary",
    "Erel_extbin_sync-packages-to-testing_resolute_amd64",
    "Erel_extbin_sync-packages-to-main",
    # Extendable isolated hierarchy (Stage 6 Gazebo & ros_workspace_shell)
    "Esrc_uR__extjetty_ros_workspace_shell__ubuntu_resolute__source",
    "Ebin_uR64__extjetty_ros_workspace_shell__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extjetty_gz-cmake__ubuntu_resolute__source",
    "Ebin_uR64__extjetty_gz-cmake__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extjetty_gz-utils__ubuntu_resolute__source",
    "Ebin_uR64__extjetty_gz-utils__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extjetty_gz-math__ubuntu_resolute__source",
    "Ebin_uR64__extjetty_gz-math__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extjetty_gz-tools2__ubuntu_resolute__source",
    "Ebin_uR64__extjetty_gz-tools2__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extjetty_gz-msgs__ubuntu_resolute__source",
    "Ebin_uR64__extjetty_gz-msgs__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extjetty_gz-transport__ubuntu_resolute__source",
    "Ebin_uR64__extjetty_gz-transport__ubuntu_resolute_amd64__binary",
    "Erel_extjetty_sync-packages-to-testing_resolute_amd64",
    "Erel_extjetty_sync-packages-to-main",
    "Esrc_uR__extlyrical_ros_workspace_shell__ubuntu_resolute__source",
    "Ebin_uR64__extlyrical_ros_workspace_shell__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extlyrical_ros_workspace__ubuntu_resolute__source",
    "Ebin_uR64__extlyrical_ros_workspace__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extlyrical_gz-demo-math__ubuntu_resolute__source",
    "Ebin_uR64__extlyrical_gz-demo-math__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extlyrical_ros_gz_interfaces__ubuntu_resolute__source",
    "Ebin_uR64__extlyrical_ros_gz_interfaces__ubuntu_resolute_amd64__binary",
    "Esrc_uR__extlyrical_ros_gz_bridge__ubuntu_resolute__source",
    "Ebin_uR64__extlyrical_ros_gz_bridge__ubuntu_resolute_amd64__binary",
    "Erel_extlyrical_sync-packages-to-testing_resolute_amd64",
    "Erel_extlyrical_sync-packages-to-main",
    # Extendable isolated hierarchy (CI)
    "Eci__nightly-release_ubuntu_resolute_amd64",
    "Eci__source-branches_ubuntu_resolute_amd64",
    "Eci__release-branches_ubuntu_resolute_amd64",
    "Eci__source-rebuild_ubuntu_resolute_amd64",
    "Eci__binary-import_ubuntu_resolute_amd64",
    "Eci__chained-import_ubuntu_resolute_amd64",
    "Eci__mixed-chain_ubuntu_resolute_amd64",
    "Eci__diamond-chain_ubuntu_resolute_amd64",
    "Eci__workspace-release_ubuntu_resolute_amd64",
    "Eci__workspace-binary-import_ubuntu_resolute_amd64",
    "Eci__gazebo-jetty-release_ubuntu_resolute_amd64",
    "Eci__gazebo-lyrical-source-rebuild_ubuntu_resolute_amd64",
    "Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64",
    # Composable hierarchy
    "Cci__nightly-release_ubuntu_resolute_amd64",
    "Cci__composable-binary_ubuntu_resolute_amd64",
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


def list_jobs(client, prefix=None):
    print(f"\nREP-159 Jobs on {client.baseurl}:")
    print("=" * 80)
    jobs_to_check = [j for j in REP159_JOBS if not prefix or j.startswith(prefix)]
    for job_name in jobs_to_check:
        try:
            job = client.get_job(job_name)
            in_queue = job.is_queued()
            running = job.is_running()
            try:
                last_build = job.get_last_build()
                status = last_build.get_status() if last_build else ("RUNNING" if running else "NO_BUILDS")
                if running and not status:
                    status = "RUNNING"
                last_num = last_build.buildno if last_build else "-"
            except Exception:
                status = "NO_BUILDS"
                last_num = "-"
            state_tag = " [QUEUED]" if in_queue else (" [BUILDING]" if running else "")
            print(f" • {job_name:<52} [Last: #{last_num} - {status}]{state_tag}")
        except Exception as e:
            print(f" • {job_name:<52} [Not Found / Error: {e}]")
    print("=" * 80)


def wait_for_build_completion(build, poll_interval=5):
    print(f"Polling build #{build.buildno} ({build.baseurl}) until completion...")
    start_ts = time.time()
    while build.is_running():
        elapsed = int(time.time() - start_ts)
        print(f"  [+{elapsed:>4}s] Build #{build.buildno} still running...")
        time.sleep(poll_interval)
        build.poll()

    status = build.get_status()
    elapsed = int(time.time() - start_ts)
    print(f"Build #{build.buildno} finished in ~{elapsed}s with status: {status}")
    print(f"Console Output: {build.baseurl}console")
    if status not in ("SUCCESS", "UNSTABLE"):
        sys.exit(1)
    return build


def wait_for_job(client, job_name, poll_interval=5, queue_wait_timeout=1800):
    if job_name not in client:
        print(f"Error: Job '{job_name}' not found on {client.baseurl}", file=sys.stderr)
        sys.exit(1)

    job = client.get_job(job_name)
    wait_start = time.time()
    while job.is_queued() and not job.is_running():
        elapsed = int(time.time() - wait_start)
        if elapsed > queue_wait_timeout:
            print(f"Timeout waiting for queued job '{job_name}' to start building.", file=sys.stderr)
            sys.exit(1)
        print(f"  [+{elapsed:>4}s] Job '{job_name}' is in queue, waiting to start...")
        time.sleep(poll_interval)
        job.poll()

    try:
        last_build = job.get_last_build()
    except Exception:
        last_build = None

    if not last_build:
        print(f"No builds found for '{job_name}'.")
        return

    if last_build.is_running():
        wait_for_build_completion(last_build, poll_interval=poll_interval)
    else:
        status = last_build.get_status()
        print(f"Job '{job_name}' latest build #{last_build.buildno} is already complete: {status} ({last_build.baseurl})")
        if status not in ("SUCCESS", "UNSTABLE"):
            sys.exit(1)


def show_server_status(client):
    resp = client.requester.get_url(f"{client.baseurl}/api/json?tree=quietingDown,quietingDownReason,mode,numExecutors")
    data = resp.json()
    print(f"\nJenkins Server Status ({client.baseurl}):")
    print("=" * 80)
    print(f" • Mode:                {data.get('mode')}")
    print(f" • Quieting Down:       {data.get('quietingDown')}")
    print(f" • Quiet Down Reason:   {data.get('quietingDownReason')}")
    print("=" * 80)

    comp_resp = client.requester.get_url(
        f"{client.baseurl}/computer/api/json?tree=computer[displayName,offline,temporarilyOffline,offlineCauseReason,numExecutors,idle,executors[currentExecutable[url,fullDisplayName]],oneOffExecutors[currentExecutable[url,fullDisplayName]]]"
    )
    comp_data = comp_resp.json()
    print("\nNodes / Agents:")
    for node in comp_data.get("computer", []):
        name = node.get("displayName")
        offline = node.get("offline")
        reason = node.get("offlineCauseReason") or ""
        running_execs = []
        for ex in (node.get("executors", []) + node.get("oneOffExecutors", [])):
            cur = ex.get("currentExecutable")
            if cur:
                running_execs.append(cur.get("fullDisplayName") or cur.get("url"))
        state = "OFFLINE" if offline else ("BUSY" if running_execs else "IDLE")
        extra = f" (Reason: {reason})" if reason else ""
        if running_execs:
            extra += f" -> Running: {', '.join(running_execs)}"
        print(f" • {name:<35} [{state}]{extra}")
    print("=" * 80)


def list_queue(client, prefix=None):
    resp = client.requester.get_url(
        f"{client.baseurl}/queue/api/json?tree=items[id,inQueueSince,why,stuck,blocked,task[name,url]]"
    )
    items = resp.json().get("items", [])
    if prefix:
        items = [it for it in items if (it.get("task", {}).get("name") or "").startswith(prefix)]

    print(f"\nJenkins Build Queue ({len(items)} items):")
    print("=" * 80)
    for it in items:
        qid = it.get("id")
        task_name = it.get("task", {}).get("name", "UNKNOWN")
        why = it.get("why", "")
        in_queue_ms = it.get("inQueueSince", 0)
        age_sec = int(time.time() - (in_queue_ms / 1000.0)) if in_queue_ms else 0
        print(f" • [ID: {qid:<6}] {task_name:<50} (queued {age_sec}s ago)")
        if why:
            print(f"     Why: {why}")
    print("=" * 80)
    return items


def clear_queue(client, prefix=None, exclude_prefix=None, queue_id=None):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if queue_id is not None:
        ids_to_cancel = [(queue_id, f"queue_id={queue_id}")]
    else:
        resp = client.requester.get_url(
            f"{client.baseurl}/queue/api/json?tree=items[id,task[name]]"
        )
        items = resp.json().get("items", [])
        if prefix:
            items = [it for it in items if (it.get("task", {}).get("name") or "").startswith(prefix)]
        if exclude_prefix:
            items = [it for it in items if not (it.get("task", {}).get("name") or "").startswith(exclude_prefix)]
        ids_to_cancel = [(it.get("id"), it.get("task", {}).get("name", "UNKNOWN")) for it in items]

    if not ids_to_cancel:
        print("No matching queue items to cancel.")
        return

    print(f"Cancelling {len(ids_to_cancel)} queue item(s)...")

    def _cancel_one(item):
        qid, name = item
        r = client.requester.post_url(f"{client.baseurl}/queue/cancelItem?id={qid}", data="")
        return qid, name, r.status_code

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(_cancel_one, it) for it in ids_to_cancel]
        done_count = 0
        for fut in as_completed(futures):
            qid, name, code = fut.result()
            done_count += 1
            if len(ids_to_cancel) <= 25 or done_count % 50 == 0 or done_count == len(ids_to_cancel):
                print(f"  [{done_count}/{len(ids_to_cancel)}] Cancelled ID {qid} ({name}) -> HTTP {code}")


def set_jobs_priority(client, priority, prefix=None):
    import re
    jobs_to_update = [j for j in REP159_JOBS if not prefix or j.startswith(prefix)]
    print(f"Setting priority={priority} on {len(jobs_to_update)} job(s) (prefix={prefix!r})...")
    for job_name in jobs_to_update:
        try:
            resp = client.requester.get_url(f"{client.baseurl}/job/{job_name}/config.xml")
            if resp.status_code != 200:
                print(f"  • {job_name}: skipped (GET config.xml HTTP {resp.status_code})")
                continue
            xml = resp.text
            new_xml, count = re.subn(
                r"(<priority>)\d+(</priority>)",
                rf"\g<1>{priority}\g<2>",
                xml,
            )
            if count == 0:
                print(f"  • {job_name}: no <priority> tag found in config.xml")
                continue
            post_resp = client.requester.post_xml_and_confirm_status(
                f"{client.baseurl}/job/{job_name}/config.xml",
                data=new_xml.encode("utf-8"),
            )
            print(f"  • {job_name:<52} -> priority={priority} (HTTP {post_resp.status_code})")
        except Exception as e:
            print(f"  • {job_name:<52} -> Error: {e}")


def verify_apt_packages(repo_base_url, prefix, suites=("building", "testing"), dist="resolute", arch="amd64"):
    import gzip
    import urllib.request

    print(f"\nVerifying APT packages with prefix '{prefix}' on {repo_base_url} ({dist}/{arch}):")
    print("=" * 80)
    for suite in suites:
        pkg_url = f"{repo_base_url.rstrip('/')}/{suite}/dists/{dist}/main/binary-{arch}/Packages.gz"
        print(f"Suite [{suite}]: {pkg_url}")
        try:
            with urllib.request.urlopen(pkg_url, timeout=30) as resp:
                raw = gzip.decompress(resp.read()).decode("utf-8", errors="replace")
            blocks = raw.strip().split("\n\n")
            matched = []
            for blk in blocks:
                pkg_name, version, filename = None, None, None
                for line in blk.splitlines():
                    if line.startswith("Package: "):
                        pkg_name = line.split(": ", 1)[1].strip()
                    elif line.startswith("Version: "):
                        version = line.split(": ", 1)[1].strip()
                    elif line.startswith("Filename: "):
                        filename = line.split(": ", 1)[1].strip()
                if pkg_name and pkg_name.startswith(prefix):
                    matched.append((pkg_name, version, filename))
            if not matched:
                print(f"  [!] No packages matching '{prefix}*' found in {suite}!")
            else:
                for p, v, fn in sorted(matched):
                    print(f"  ✓ {p:<38} Version: {v:<18} ({fn})")
        except Exception as e:
            print(f"  [Error fetching {pkg_url}: {e}]")
    print("=" * 80)


def show_job_status(client, job_name):
    if job_name not in client:
        print(f"Error: Job '{job_name}' not found on {client.baseurl}", file=sys.stderr)
        sys.exit(1)

    job = client.get_job(job_name)
    in_queue = job.is_queued()
    running = job.is_running()
    print(f"Job: {job_name}")
    print(f"  URL:       {job.baseurl}")
    print(f"  In Queue:  {in_queue}")
    print(f"  Running:   {running}")
    try:
        last_build = job.get_last_build()
        if last_build:
            status = last_build.get_status() or ("RUNNING" if last_build.is_running() else "UNKNOWN")
            print(f"  Last Build: #{last_build.buildno} - {status} ({last_build.baseurl})")
    except Exception:
        print("  Last Build: NO_BUILDS")


def show_console(client, job_name, build_num=None, tail=None, grep_pattern=None):
    import re
    if job_name not in client:
        print(f"Error: Job '{job_name}' not found on {client.baseurl}", file=sys.stderr)
        sys.exit(1)

    job = client.get_job(job_name)
    build = job.get_build(build_num) if build_num else job.get_last_build()
    console_text = build.get_console()
    lines = console_text.splitlines()
    if grep_pattern:
        regex = re.compile(grep_pattern)
        lines = [line for line in lines if regex.search(line)]
    if tail and tail > 0:
        lines = lines[-tail:]
    print(f"=== Console output for {job_name} #{build.buildno} ({build.get_status() or 'RUNNING'}) ===")
    print("\n".join(lines))


def trigger_job(client, job_name, watch=False, wait=False, poll_interval=5):
    if job_name not in client:
        print(f"Error: Job '{job_name}' not found on {client.baseurl}", file=sys.stderr)
        sys.exit(1)

    try:
        srv = client.requester.get_url(f"{client.baseurl}/api/json?tree=quietingDown,quietingDownReason").json()
        if srv.get("quietingDown"):
            print(
                f"WARNING: Jenkins controller is in Prepare-for-Shutdown (quietingDown=True, reason={srv.get('quietingDownReason')!r}). "
                "New builds will remain in queue until quiet-down is cancelled.",
                file=sys.stderr,
            )
    except Exception:
        pass

    job = client.get_job(job_name)
    print(f"Triggering build for: {job_name} ...")
    queue_item = job.invoke()
    print(f"Job successfully queued! Queue ID: {queue_item.queue_id}")

    if watch or wait:
        print("Waiting for build to leave queue and start execution...")
        build = queue_item.block_until_building()
        print(f"Build started: #{build.buildno} ({build.baseurl})")
        print(f"Console Output: {build.baseurl}console")
        if wait:
            wait_for_build_completion(build, poll_interval=poll_interval)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and trigger REP-159 CI and Release jobs on Jenkins"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_JENKINS_URL,
        help=f"Jenkins base URL (default: {DEFAULT_JENKINS_URL})",
    )
    parser.add_argument(
        "--job",
        help="Specific job name to trigger or inspect",
    )
    parser.add_argument(
        "--jobs",
        nargs="+",
        help="Sequence of job names to trigger and wait for sequentially",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List status of all REP-159 test jobs",
    )
    parser.add_argument(
        "--prefix",
        help="Filter --list, --queue-list, --queue-clear, or --stop-running by job name prefix (e.g. 'E', 'R')",
    )
    parser.add_argument(
        "--exclude-prefix",
        help="Exclude jobs starting with this prefix in --queue-clear or --stop-running (e.g. 'E')",
    )
    parser.add_argument(
        "--server-status",
        action="store_true",
        help="Show Jenkins controller status (quietingDown, mode) and node/executor states",
    )
    parser.add_argument(
        "--queue-list",
        action="store_true",
        help="List items currently in the Jenkins build queue (optionally filtered by --prefix)",
    )
    parser.add_argument(
        "--queue-clear",
        action="store_true",
        help="Cancel items in the Jenkins build queue (optionally filtered by --prefix / --exclude-prefix)",
    )
    parser.add_argument(
        "--queue-cancel",
        type=int,
        help="Cancel a specific Jenkins queue item by Queue ID",
    )
    parser.add_argument(
        "--set-priority",
        type=int,
        help="Set <priority>N</priority> on REP-159 jobs (optionally filtered by --prefix, e.g. --prefix E --set-priority 1)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch build until it leaves queue and starts execution",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Trigger build (unless --wait-only) and block until build completes",
    )
    parser.add_argument(
        "--wait-only",
        action="store_true",
        help="Do not trigger a new build; wait for an in-queue or running build of --job to complete",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show status of --job without triggering a build",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Show console output of --job (latest build or --build NUM)",
    )
    parser.add_argument(
        "--build",
        type=int,
        help="Specific build number for --console",
    )
    parser.add_argument(
        "--tail",
        type=int,
        help="Show only the last N lines of console output",
    )
    parser.add_argument(
        "--grep",
        help="Regex filter for --console lines",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Polling interval in seconds for --wait / --wait-only (default: 5)",
    )
    parser.add_argument(
        "--verify-apt-prefix",
        help="Verify packages starting with prefix in APT repo (e.g. 'vendor-extendable-')",
    )
    parser.add_argument(
        "--apt-repo-url",
        default="http://repo.test.ros2.org/ubuntu",
        help="Base APT repo URL for --verify-apt-prefix (default: http://repo.test.ros2.org/ubuntu)",
    )

    args = parser.parse_args()

    if args.verify_apt_prefix:
        verify_apt_packages(args.apt_repo_url, args.verify_apt_prefix)
        if not args.job and not args.jobs and not args.list and not args.server_status and not args.queue_list:
            return

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

    action_taken = False
    if args.server_status:
        show_server_status(client)
        action_taken = True
    if args.queue_list:
        list_queue(client, prefix=args.prefix)
        action_taken = True
    if args.queue_clear:
        clear_queue(client, prefix=args.prefix, exclude_prefix=args.exclude_prefix)
        action_taken = True
    if args.queue_cancel is not None:
        clear_queue(client, queue_id=args.queue_cancel)
        action_taken = True
    if args.set_priority is not None:
        set_jobs_priority(client, args.set_priority, prefix=args.prefix)
        action_taken = True

    if args.list or (not args.job and not args.jobs and not action_taken):
        list_jobs(client, prefix=args.prefix)
        if not args.job and not args.jobs:
            print("\nTip: Specify --job <JOB_NAME> to trigger or inspect a build.")
            return

    if args.jobs:
        total = len(args.jobs)
        for idx, jname in enumerate(args.jobs, 1):
            mode_str = "Waiting for" if args.wait_only else "Executing"
            print(f"\n[{idx}/{total}] === {mode_str} Sequential Step: {jname} ===")
            if args.wait_only:
                wait_for_job(client, jname, poll_interval=args.poll_interval)
            else:
                trigger_job(client, jname, watch=True, wait=True, poll_interval=args.poll_interval)
        print(f"\nAll {total} sequential jobs completed successfully!")
        return

    if args.job:
        if args.status:
            show_job_status(client, args.job)
        elif args.console:
            show_console(client, args.job, build_num=args.build, tail=args.tail, grep_pattern=args.grep)
        elif args.wait_only:
            wait_for_job(client, args.job, poll_interval=args.poll_interval)
        else:
            trigger_job(client, args.job, watch=args.watch, wait=args.wait, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
