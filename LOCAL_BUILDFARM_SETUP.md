# Local ROS Buildfarm Testing Setup & Development Roadmap

This guide documents the generic configuration of the **local ROS Buildfarm testing environment** for validating **[REP-159](https://github.com/openrobotics/reps/pull/32)** extensible distributions (`upstream`, `srcext`, `binext`), along with the planned development roadmap.

> [!NOTE]
> All host-specific IPs, internal network topologies, and secret tokens have been sanitized. This setup describes the reproducible architecture for running the test harness locally.

---

## 1. Local Buildfarm Architecture

```
┌─────────────────────────────────┐        WebSocket         ┌──────────────────────────────────────┐
│         Jenkins Master          │ ◄─────────────────────── │      Jenkins Docker Agent (amd64)    │
│  • Jenkins 2.x LTS              │                          │  • Based on jenkins/inbound-agent    │
│  • ros_buildfarm Jenkins plugins│                          │  • Docker CLI + socket mounted (DooD)│
│  • Config: index-local.yaml     │                          │  • Label: ci-agent, linux, amd64     │
└─────────────────────────────────┘                          └───────────────────┬──────────────────┘
                                                                                 │ Launches inner
                                                                                 ▼ build containers
                                                             ┌──────────────────────────────────────┐
                                                             │      Docker Engine on Agent Host     │
                                                             │  • Ubuntu Resolute build containers  │
                                                             │  • Colcon workspace builds & tests   │
                                                             └──────────────────────────────────────┘
```

---

## 2. Jenkins Master Configuration

### 2.1 Required Jenkins Plugins
The ROS Buildfarm job generators (`generate_ci_jobs.py`, `generate_release_jobs.py`) require the following standard upstream plugin suite:
- `git` & `github` (SCM operations and notifications)
- `matrix-project` (Multi-platform matrices)
- `xunit` (Test report parsing)
- `parameterized-trigger` (Pipeline chaining between build & import jobs)
- `ansicolor` (Console color formatting)
- `PrioritySorter` (Job queue prioritization)
- `description-setter` (Build metadata and version tagging)
- `dashboard-view` (Aggregated build farm status)
- `publish-over-ssh` & `publish-over` (Artifact upload to repo server)
- `ssh-agent` (SSH credential binding)
- `timestamper` (Console timestamps)
- `build-timeout` (Job timeout protection)
- `email-ext` & `mailer` (Notifications)
- `groovy` & `groovy-postbuild` (Pipeline logic and health checks)
- `copyartifact` & `rebuild` (Artifact propagation and manual re-runs)

### 2.2 Agent Node Registration
On the Jenkins Master (`Manage Jenkins` $\to$ `Nodes` $\to$ `New Node`):
- **Node Name**: `ci-agent-amd64`
- **Executors**: `4` (or number of available CPU cores)
- **Remote root directory**: `/home/jenkins/agent`
- **Labels**: `ci-agent amd64 linux buildagent`
- **Usage**: *Only build jobs with label expressions matching this node*
- **Launch method**: *Launch agent by connecting it to the controller* (WebSocket enabled)

---

## 3. Docker Agent Configuration (DooD)

To run ROS Buildfarm jobs, the agent requires Docker access to spawn inner task containers for workspace generation, compilation, and testing.

### 3.1 Agent Dockerfile
The agent image is built on top of `jenkins/inbound-agent:latest` with the Python buildfarm runtime dependencies pre-installed:

```dockerfile
FROM jenkins/inbound-agent:latest
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-yaml \
    python3-empy \
    python3-rosdistro \
    python3-catkin-pkg \
    git \
    curl \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*
USER jenkins
```

### 3.2 Docker Compose Service
The agent is declared in `docker-compose.yml` with Docker-out-of-Docker (DooD) socket and binary mounts:

```yaml
services:
  jenkins-agent-amd64:
    build:
      context: ./config/jenkins-agent
      dockerfile: Dockerfile
    image: local/jenkins-agent-buildfarm:latest
    container_name: jenkins-agent-amd64
    restart: unless-stopped
    environment:
      - JENKINS_URL=http://<jenkins-master-host>:8080/
      - JENKINS_AGENT_NAME=ci-agent-amd64
      - JENKINS_SECRET=<agent-secret-token>
      - JENKINS_AGENT_WORKDIR=/home/jenkins/agent
      - JENKINS_WEB_SOCKET=true
    group_add:
      - "<docker-host-group-id>" # e.g. 991 or $(getent group docker | cut -d: -f3)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/bin/docker:/usr/bin/docker:ro
      - /home/jenkins/agent:/home/jenkins/agent
```

### 3.3 Local APT Repository Service (`apt-repo` & `reprepro`)
To emulate the OSRF repository pipeline (`repo.ros2.org` / `repo.test.ros2.org`), a lightweight APT repository container (`nginx:alpine`) runs on the Docker host, backed by `reprepro` and local GPG package signing:

```yaml
  apt-repo:
    image: nginx:alpine
    container_name: apt-repo
    restart: unless-stopped
    ports:
      - "8088:80"
    volumes:
      - ./config/apt-repo:/usr/share/nginx/html:ro
```

- **Repository URL**: `http://<docker-host-ip>:8088/ubuntu/building`
- **Distributions Managed**: `resolute` (`building`, `shadow-fixed`, `main`)
- **Key Management**: Signed with local GPG key (`buildfarm@local`), with public key served at `http://<docker-host-ip>:8088/ubuntu/ros-local-buildfarm.asc`.
- **Package Ingestion**:
  ```bash
  # Ingest binary debian package into building channel
  reprepro -b /root/config/apt-repo/ubuntu/building includedeb resolute /path/to/pkg.deb

  # Snapshot sync from building to shadow-fixed (testing)
  reprepro -b /root/config/apt-repo/ubuntu/shadow-fixed copysrc resolute resolute <package>
  ```

> [!IMPORTANT]
> **DooD Workspace Path Parity**: The agent directory `/home/jenkins/agent` inside the container **must map to the identical path `/home/jenkins/agent` on the host**. 
> When `ros_buildfarm` invokes `docker run -v $WORKSPACE/...:/tmp/...`, the Docker daemon running on the host interprets the volume source on the host filesystem. Path parity ensures inner container mounts resolve seamlessly.

---

## 4. Local Buildfarm Validation Results

All 5 REP-159 CI test jobs run cleanly to **100% SUCCESS** on the local buildfarm:

| Job | Description | Extension Method | Result |
|---|---|---|---|
| `Uci__nightly-release_ubuntu_resolute_amd64` | Upstream base release packages | None (Base) | **SUCCESS** |
| `Uci__release-branches_ubuntu_resolute_amd64` | Bloom releases (`ament_cmake_core`, `upstream_c`) | None (Base) | **SUCCESS** |
| `Uci__source-branches_ubuntu_resolute_amd64` | Direct `main` branches of sources | None (Base) | **SUCCESS** |
| `Sci__nightly-release_ubuntu_resolute_amd64` | Cross-distro source rebuild of upstream deps | `source_rebuild` | **SUCCESS** |
| `Bci__nightly-release_ubuntu_resolute_amd64` | Downstream uses upstream binaries from underlay | `binary_import` | **SUCCESS** |

---

## 5. Development Roadmap: Incremental Execution Phases & Architectural Options

We organize all remaining development into an **ultra-incremental execution path**, documenting all architectural options, design trade-offs, and an immediate step-by-step pipeline.

### 5.1 Architectural & Design Options Matrix

| Dimension | Option | Specification / Syntax | Pros | Cons / Dependencies | Status & Priority |
|:---|:---|:---|:---|:---|:---:|
| **Binary Renaming** | **Option A.1: Declarative Regex (`binary_rule`)** | `binary_rule:`<br>&nbsp;&nbsp;`search: '^'`<br>&nbsp;&nbsp;`replace: 'vendor-{DISTRO}-'` | Zero external dependencies, pure Python stdlib, easily auditable in YAML, invertible for `rosdep` reverse resolution. | Regex pattern syntax requires escaping special characters. | **Prioridad 1** *(Seleccionada. Si funciona, se continúa sin probar las otras)* |
| | **Option A.2: Jinja2 Templates** | `binary_template: "{{ distro }}-{{ package }}"` | Clean sandboxed syntax; widely recognized templating syntax. | Adds mandatory `jinja2` dependency to `rosdistro` and `rosdep`. | **Prioridad 2** *(Explorada en rama dedicada, fallback)* |
| | **Option A.3: EmPy Templates** | `binary_template: "@(distro)-@(package)"` | Consistent with `ros_buildfarm` internal templates; rich python expressions. | Security risk (arbitrary code execution); process stdout hijacking. | **Prioridad 3** *(Explorada en rama dedicada, fallback)* |
| **Install Prefixes** | **Option B.1: Distribution-level Prefix** *(Selected)* | `install_rule:`<br>&nbsp;&nbsp;`prefix: '/opt/vendor/{distro}'` | Simple, centralized layout definition for entire vendor distribution. | Fixed path across all packages in the distribution. | ✅ Implemented & Unit-Tested |
| | **Option B.2: Granular / Regex Rule** | `install_rule:`<br>&nbsp;&nbsp;`rules:`<br>&nbsp;&nbsp;&nbsp;&nbsp;`- search: '^gz-'`<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`prefix: '/usr'` | Supports mixed-origin distributions (e.g. system libs in `/usr`, ROS in `/opt/ros`). | More verbose YAML specification. | ✅ Implemented & Unit-Tested |
| | **Option B.3: Standard Fallback** | *(Omitted)* $\to$ default `/opt/ros/{distro}` | 100% backward compatible with vanilla ROS 2 distros. | Inflexible for non-standard or vendor-customized filesystems. | ✅ Active Default |
| **Topologies** | **Option C.1: Single-level Binary Extension** | `extends:`<br>&nbsp;&nbsp;`- name: upstream`<br>&nbsp;&nbsp;&nbsp;&nbsp;`type: binary_import` | Direct downstream consumption of pre-built upstream Debian packages. | Upstream packages must already be built and available in an APT repo. | ✅ Active Phase 1 & 2 |
| | **Option C.2: Single-level Source Extension** | `extends:`<br>&nbsp;&nbsp;`- name: upstream`<br>&nbsp;&nbsp;&nbsp;&nbsp;`type: source_rebuild` | Builds entire upstream dependency chain from git in CI without debian packages. | Higher build times; does not test Debian package boundary. | ✅ Validated (`Sci` 100%) |
| | **Option C.3: Chained Multi-level ($A \to B \to C$)** | `chained_ext` $\to$ `srcext` $\to$ `upstream` | Proves recursive multi-tier dependency walk across multi-level extensions. | Requires coordinating 3 distribution definitions. | Planned (Phase 6) |
| | **Option C.4: Multi-parent Diamond ($D \to [A, B]$)** | `diamond_ext` $\to$ `[upstream, vendor_base]` | Proves multiple simultaneous parents and collision detection guardrails. | Requires resolving cross-parent name and underlay ordering. | Planned (Phase 6) |
| | **Option C.5: Remote Distributed Index** | `extends:`<br>&nbsp;&nbsp;`- name: upstream`<br>&nbsp;&nbsp;&nbsp;&nbsp;`index_url: http://remote...` | Proves distributed ownership of parent distributions across distinct servers. | Requires external network accessibility and caching strategy. | Planned (Phase 6) |
| **Infrastructure** | **Option D.1: Dual Index Configuration** *(Selected)* | `index-local.yaml` (Local cluster)<br>`index-rep159.yaml` (Remote test farm) | Absolute isolation; zero risk of polluting remote test farm configs with local IPs. | Requires keeping package lists synchronized between the two files. | ✅ Active |
| | **Option D.2: Automated Switcher Script** | `./scripts/switch_target_farm.sh local\|remote` | Single command sets symlinks, environment variables, and Jenkins endpoints. | Requires maintaining helper script. | Planned (Phase 3) |

---

### 5.2 Ultra-Incremental Execution Roadmap

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   INCREMENTAL EXECUTION ROADMAP                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Phase 1: Complete Upstream Binary Chain (Release of `upstream_b` & `upstream_c`) [DONE]          │
│ • Step 1.1: Release `upstream_a` (Sourcedeb #10, Binarydeb #4, Sync to testing #3)   [DONE]      │
│ • Step 1.2: Release `upstream_b` (Sourcedeb #1, Binarydeb #1)                       [DONE]      │
│ • Step 1.3: Release `upstream_c` (Sourcedeb #1, Binarydeb #2)                       [DONE]      │
│ • Step 1.4: Sync full 3-tier upstream hierarchy to `testing` repo via `Urel_sync #4` [DONE]      │
│                                                                                                  │
│ Phase 2: True Downstream Binary Consumption (`Bci` with Real APT Packages)         [DONE]        │
│ • Run `Bci__nightly-release_ubuntu_resolute_amd64` consuming real `ros-upstream-upstream-c`. [DONE]│
│ • Validate end-to-end `binary_import`: zero upstream git checkouts; debs installed via apt/rosdep│
│                                                                                                  │
│ Phase 3: Infrastructure Portability & Remote Test Farm Interchangeability                        │
│ • Provide seamless toggle (`local` vs `remote`) between local cluster and `build.test.ros2.org`. │
│ • Keep upstream-facing PR branches (`feat/<name>`) 100% clean and rebased against `master`.       │
│                                                                                                  │
│ Phase 4: Declarative Binary Renaming (`FEAT-1` & `FEAT-3`: `binary_rule`)                        │
│ • Configure custom `binary_rule` in test distribution (e.g. `vendor-{DISTRO}-` prefix).          │
│ • Validate binary deb packaging with custom names and `rosdep` reverse resolution.               │
│                                                                                                  │
│ Phase 5: Dynamic Install Prefixes (`FEAT-2`: `install_rule`)                                     │
│ • Validate custom install prefix (`/opt/vendor/{distro}`) in release/binarydeb & CI underlays.   │
│                                                                                                  │
│ Phase 6: Advanced Extension Topologies (Chaining, Diamond, Remote Index)                         │
│ • Validate Chained Extension ($A \to B \to C$) and Diamond Multi-Parent ($D \to [A, B]$).        │
│                                                                                                  │
│ Phase 7: Upstream Submission & PR Finalization                                                   │
│ • Clean rebase on upstream `master`, final test suite run, and submit official Pull Requests.     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Branching Strategy & Development Workflow

To maintain clean traceability and ensure experiments mirror what will eventually run in the remote test buildfarm (`build.test.ros2.org`), development follows these principles:

1. **Clean Upstream PR Branches (`feat/<name>`)**:
   - Cut directly from **`master`** of each submodule (no experimental baggage or local hacks).
   - Candidate branches for Pull Requests to Open Robotics repositories.
2. **Integration / Test Branches (`test/rep159-<name>`)**:
   - Based on the `rep159` integration branch.
   - Contain local test scaffolding, Docker template overrides, and local cluster endpoints.
3. **Configuration Portability (`local` vs `remote`)**:
   - `submodules/ros_buildfarm_config/index-local.yaml` points to local APT repo (`192.168.30.202:8088`) and local Jenkins (`192.168.30.206:8080`).
   - `submodules/ros_buildfarm_config/index-rep159.yaml` points to remote test farm repositories and upstream URLs.
   - Switching between them requires zero code modifications in core libraries.
4. **Minimal Submodule Invasiveness**:
   - Submodules remain as close to upstream as possible to ensure seamless transfer to `build.test.ros2.org`.

