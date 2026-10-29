# Stage 2: Custom Install Rules & Dynamic Underlays

## 1. Executive Summary & Problem Statement

In earlier iterations of REP-159 (such as initial prototyping in commit `9807b32`), the buildfarm assumed all parent distributions resided under the standard path `/opt/ros/%s`.
This assumption fails in two critical scenarios:
1. **Custom Vendor Installation Hierarchies**: Enterprise deployments that install ROS software into custom prefixes such as `/opt/vendor/{distro}`, `/opt/acme/ros2`, or `/usr` (e.g., system-wide Gazebo packages).
2. **Dynamic Underlay Resolution in `binary_import`**: When an overlay distribution imports pre-built binaries from a parent, the build environment must automatically identify where the parent packages are installed, source their setup hooks, and expose their CMake config directories.

Stage 2 introduces the **`install_rule`** specification in `rosdistro` and the **`ROS_BUILDFARM_PARENT_RESULT_SPACES`** dynamic underlay injection mechanism in `ros_buildfarm`.

---

## 2. Design Decisions & Technical Rationale

### Decision 1: Declarative `install_rule` Schema
* **Specification**: Added `install_rule` at distribution and repository levels supporting both simple path templates and regex substitutions:
  ```yaml
  install_rule: /opt/vendor/{distro}
  ```
  Or using explicit regex transformation:
  ```yaml
  install_rule:
    search: '^'
    replace: '/opt/vendor/'
  ```
* **Rationale**: Simple string templating covers 99% of ROS use cases, while regex support provides uniformity with `binary_rule`.

### Decision 2: Dynamic Parent Result Space Calculation (`ROS_BUILDFARM_PARENT_RESULT_SPACES`)
* **Problem**: How to communicate the parent installation paths to CI containers without hardcoding them in Dockerfiles or job scripts.
* **Adopted Solution**: `ros_buildfarm.common.get_binary_import_underlays()` recursively inspects the `extends:` tree in `distribution.yaml`, computes the prefix for each parent distribution using its `install_rule`, and exports them in the environment variable `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
* **CI Job Execution Flow**:
  1. `ros_buildfarm` calculates parent prefixes: e.g., `ROS_BUILDFARM_PARENT_RESULT_SPACES=/opt/vendor/upstream`.
  2. Inside the container, `build_and_install.py` inspects `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
  3. Colcon workspace configuration automatically appends `--cmake-args -DCMAKE_PREFIX_PATH="/opt/vendor/upstream"` and invokes `. /opt/vendor/upstream/setup.sh`.

---

## 3. Implementation Breakdown: Core Code vs. Testing Tweaks

### Core Implementation (To be Merged Upstream)

1. **`ros/rosdistro` (Branch: `feature/rep159-install-rule`)**:
   - `DistributionFile`: Adds `install_rule` parsing and `get_distribution_install_prefix()`.
   - `ReleaseRepositorySpecification`: Adds repository-level `install_rule` support.
   - Context evaluation: Replaces `{distro}` and `{package}` placeholders.

2. **`ros-infrastructure/ros_buildfarm` (Branch: `feat/install-prefixes`)**:
   - `common.py`: Implements `get_distribution_install_prefix(dist_file)` and `get_binary_import_underlays(dist_file, rosdistro_name)`.
   - `release_job.py` and `ci_job.py`: Export `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
   - `ci_task.Dockerfile.em`: Passes parent result space variables to the build environment.

### Testing Tweaks & Local Workarounds (Test Harness Only — Do NOT Upstream)

1. **Remote Testfarm Prefix Alignment**:
   - On the local testbed, packages were built with `install_rule: /opt/vendor/{distro}`.
   - When running on `build.test.ros2.org`, the pre-built `.deb` packages already present in `repo.test.ros2.org/ubuntu/testing` were installed under `/opt/ros/upstream`.
   - In job `Bci__nightly-release` Build #5, injecting `/opt/vendor/upstream` failed because the remote `.deb` files resided in `/opt/ros/upstream`.
   - *Fix for testing*: `rep159-rosdistro` was updated on the testfarm branch to match the actual location (`install_rule: /opt/ros/{distro}`).
2. **Container Pip Injections**:
   - Injected git tarball install of `rosdistro` into `ci_task.Dockerfile.em` during local testing.

---

## 4. Empirical Validation & Test Evidence

### Local Test Suites
* **`tools/validate_install_prefixes.py` (Suite 7)**: 100% pass across custom paths, templated variables, and fallback to default `/opt/ros/{distro}`.

### Jenkins CI Job Evidence

* **Local Buildfarm (`192.168.30.206`)**:
  - `Bci__nightly-release_ubuntu_resolute_amd64` (#2): **SUCCESS** — Dynamic underlay resolution via `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
  - `Bci__nightly-release_ubuntu_resolute_amd64` (#7): **SUCCESS** — Injected `/opt/vendor/upstream`, sourced `. /opt/vendor/upstream/setup.sh`, compiled `downstream_bin_a`, and passed all unit tests 100% green.

* **Remote Testfarm (`build.test.ros2.org`)**:
  - `Bci__nightly-release_ubuntu_resolute_amd64` (#6): **SUCCESS** — Injected `/opt/ros/upstream`, resolved `upstream_cConfig.cmake`, compiled `downstream_bin_a`, and executed tests green on public OSRF runners.

---

## 5. Upstream PR & Release Roadmap

1. **PR 1: `ros/rosdistro`**
   - *Title*: `feat(install_rule): add configurable distribution and repository installation prefixes`
   - *Branch*: `feature/rep159-install-rule` $\to$ `master`
   - *Release Target*: Included in `rosdistro >= 1.0.0`.
2. **PR 2: `ros-infrastructure/ros_buildfarm`**
   - *Title*: `feat(underlays): dynamically compute parent result spaces via install_rule`
   - *Branch*: `feat/install-prefixes` $\to$ `master`
   - *Release Target*: Included in `ros_buildfarm >= 4.2.0`.
