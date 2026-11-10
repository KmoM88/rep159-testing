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

1. **`ros/rosdistro` (Branch: `feat/rep159-install-rule`, commit `4916cae`)**:
   - Stacked cleanly on `feature/rep159-binary-naming-regex` (`bfde799`).
   - `DistributionFile`: Adds `install_rule` parsing and `get_distribution_install_prefix()`.
   - `ReleaseRepositorySpecification`: Adds repository-level `install_rule` support.
   - Context evaluation: Replaces `{distro}` and `{package}` placeholders.
   - Verification: 91/91 unit tests passing.

2. **`ros-infrastructure/ros_buildfarm` (Branch: `feat/rep159-underlays`, commit `902ccb1`, PR 3B)**:
   - Clean PR-ready branch cut directly off `origin/master` (zero Dockerfile pip hacks).
   - `common.py`: Implements `get_distribution_install_prefix(dist_file)` and recursive `get_binary_import_underlays(dist_file, rosdistro_name)`.
   - `release_job.py` and `ci_job.py`: Export `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
   - `workspace.py`: Dynamic environment export (`CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, multiarch `LD_LIBRARY_PATH`) for pure-CMake underlays lacking `setup.sh`.
   - Verification: 10/10 underlay tests + flake8 passing 100% green.

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

* **Remote Testfarm (`https://build.test.ros2.org` & `http://repo.test.ros2.org`)**:
  - **Pure CMake `extendable` / `extendablebin` / `extendablesrc` Suite (`install_rule: '/opt/vendor/{distro}'`)**:
    - **Custom Prefix Release & Sync Pipeline (`/opt/vendor/extendable`)**:
      - [`Esrc_uR__upstream_a #3`](https://build.test.ros2.org/job/Esrc_uR__upstream_a__ubuntu_resolute__source/3/) ([Console](https://build.test.ros2.org/job/Esrc_uR__upstream_a__ubuntu_resolute__source/3/console)), [`Esrc_uR__upstream_b #2`](https://build.test.ros2.org/job/Esrc_uR__upstream_b__ubuntu_resolute__source/2/) ([Console](https://build.test.ros2.org/job/Esrc_uR__upstream_b__ubuntu_resolute__source/2/console)), [`Esrc_uR__upstream_c #2`](https://build.test.ros2.org/job/Esrc_uR__upstream_c__ubuntu_resolute__source/2/) ([Console](https://build.test.ros2.org/job/Esrc_uR__upstream_c__ubuntu_resolute__source/2/console)): **SUCCESS** — Packaged from dedicated Stage 2 release tracks (`debian/vendor-extendable-install-rule/resolute/upstream_{a,b,c}`) with `-DCMAKE_INSTALL_PREFIX="/opt/vendor/extendable"`.
      - [`Ebin_uR64__upstream_a #2`](https://build.test.ros2.org/job/Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary/2/) ([Console](https://build.test.ros2.org/job/Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary/2/console)), [`Ebin_uR64__upstream_b #2`](https://build.test.ros2.org/job/Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary/2/) ([Console](https://build.test.ros2.org/job/Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary/2/console)), [`Ebin_uR64__upstream_c #2`](https://build.test.ros2.org/job/Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary/2/) ([Console](https://build.test.ros2.org/job/Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary/2/console)): **SUCCESS** — Built `.deb` binaries installing under `/opt/vendor/extendable`.
      - [`Erel_sync-packages-to-testing_resolute_amd64 #9`](https://build.test.ros2.org/job/Erel_sync-packages-to-testing_resolute_amd64/9/) ([Console](https://build.test.ros2.org/job/Erel_sync-packages-to-testing_resolute_amd64/9/console)): **SUCCESS** — Promoted [`vendor-extendable-upstream-a_0.1.0-1resolute.20261110.003705_amd64.deb`](http://repo.test.ros2.org/ubuntu/testing/pool/main/v/vendor-extendable-upstream-a/vendor-extendable-upstream-a_0.1.0-1resolute.20261110.003705_amd64.deb), [`vendor-extendable-upstream-b_0.1.0-1resolute.20261110.004112_amd64.deb`](http://repo.test.ros2.org/ubuntu/testing/pool/main/v/vendor-extendable-upstream-b/vendor-extendable-upstream-b_0.1.0-1resolute.20261110.004112_amd64.deb), and [`vendor-extendable-upstream-c_0.1.0-1resolute.20261110.004146_amd64.deb`](http://repo.test.ros2.org/ubuntu/testing/pool/main/v/vendor-extendable-upstream-c/vendor-extendable-upstream-c_0.1.0-1resolute.20261110.004146_amd64.deb) to [`testing/Packages.gz`](http://repo.test.ros2.org/ubuntu/testing/dists/resolute/main/binary-amd64/Packages.gz).
    - **Downstream CI Validation (`binary_import` & `source_rebuild`)**:
      - [`Eci__binary-import_ubuntu_resolute_amd64 #5`](https://build.test.ros2.org/job/Eci__binary-import_ubuntu_resolute_amd64/5/) ([Console](https://build.test.ros2.org/job/Eci__binary-import_ubuntu_resolute_amd64/5/console)): **SUCCESS** — Halted source walk at `binary_import` boundary (cloning only `downstream_bin_a`), resolved and installed `vendor-extendable-upstream-c` via APT into `/opt/vendor/extendable`, injected `ROS_BUILDFARM_PARENT_RESULT_SPACES=/opt/vendor/extendable`, exported `CMAKE_PREFIX_PATH` & `LD_LIBRARY_PATH` to `/opt/vendor/extendable`, and passed 1/1 CTest report.
      - [`Eci__source-rebuild_ubuntu_resolute_amd64 #2`](https://build.test.ros2.org/job/Eci__source-rebuild_ubuntu_resolute_amd64/2/) ([Console](https://build.test.ros2.org/job/Eci__source-rebuild_ubuntu_resolute_amd64/2/console)): **SUCCESS** — Cloned and built all 4 source packages (`upstream_{a,b,c}` + `downstream_src_a`) in topological order and passed 4/4 CTest reports.
  - **AMENT `binext` Suite (`B*` jobs)**:
    - `Bci__nightly-release_ubuntu_resolute_amd64` (#6): **SUCCESS** — Injected `/opt/ros/upstream`, resolved `upstream_cConfig.cmake`, compiled `downstream_bin_a`, and executed tests green on public OSRF runners.

---

## 5. Release-Gated Upstream PR & Release Sequence

1. **Wave 0 — `openrobotics/reps` (Spec Follow-Up)**:
   - Add formal `install_rule` schema & resolution precedence section to `_posts/rep-0159:2026.md` on `openrobotics:rosdistro_extension` (building on [`openrobotics/reps#35`](https://github.com/openrobotics/reps/pull/35)).
2. **Wave 0 — `ros-infrastructure/rosdistro`**:
   - *Title*: `feat(rep159): support install_rule for custom installation prefixes and dynamic underlay resolution`
   - *Branch*: `feat/rep159-install-rule` (`4916cae`, stacked on `feature/rep159-binary-naming-regex` @ `bfde799`) $\to$ `master` (org base: `rep159`).
   - *Release Gate 1*: Must ship in **`rosdistro >= 1.2.0`** (PyPI + `ros_bootstrap` APT `python3-rosdistro-modules >= 1.2.0`) before Wave 3.
3. **Wave 3 — `ros-infrastructure/ros_buildfarm` (PR 3B)**:
   - *Prerequisite Gates*: **Gate 1 (`rosdistro >= 1.2.0`)** + **Gate 2 (`rosdep >= 0.27.0`)** published in `ros_bootstrap` APT & PyPI so temporary `create_workspace.Dockerfile.em` tarball `pip3 install` commits (`40231f3`, `4f4b059`) can be dropped.
   - *Title*: `feat(underlays): dynamically compute parent result spaces via install_rule and support pure-CMake underlays`
   - *Branch*: `feat/rep159-underlays` (`902ccb1`, clean off `origin/master`) $\to$ `master`.
   - *Release Gate 4*: Ships in **`ros_buildfarm >= 4.2.0`**.
