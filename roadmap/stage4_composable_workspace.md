# Stage 4: Composable Suite, Native Sourcing & Bloom Integration

## 1. Executive Summary & Problem Statement

In Stages 1 through 3, topological validation relied on pure CMake packages and environment variable injection by `ros_buildfarm` (`CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`).
However, a standard ROS 2 distribution requires two critical elements:
1. **Native Shell Environment (`ros_workspace`)**: ROS 2 packages rely on `/opt/ros/<distro>/setup.sh`, which parses `.dsv` environment hooks, sets up `AMENT_PREFIX_PATH`, and recursively sources parent distribution underlays.
2. **Automated Packaging Tooling (`bloom`)**: Upstream `bloom` hardcodes Debian package names as `ros-<distro>-<pkg>` and installation prefixes as `/opt/ros/<distro>`, making it impossible to release REP-159 compliant packages without manual packaging overrides.

Stage 4 establishes the **`composable` distribution suite**, integrates **`ros_workspace` underlay chaining**, and enhances **`bloom`** to natively generate Debian packaging complying with `binary_rule` and `install_rule`.

---

## 2. Design Decisions & Technical Rationale

### Decision 1: Native Setup Sourcing vs. Buildfarm Variable Injection
* **Evaluation**: While injecting environment variables at the buildfarm level worked for pure CMake packages, it does not evaluate package-specific `.dsv` environment hooks, ament resource index paths, or Python module paths.
* **Adopted Solution**: Package `ros_workspace` as a foundational Debian package installed into `/opt/ros/<distro>`. Buildfarm CI jobs detect the presence of `/opt/ros/<distro>/setup.sh` and execute all build and test steps within that native shell context:
  ```bash
  . /opt/ros/<distro>/setup.sh && colcon build ...
  . /opt/ros/<distro>/setup.sh && colcon test ...
  ```

### Decision 2: Underlay Chaining in `ros_workspace`
* **Mechanism**: In `submodules/ros_workspace` on branch `feat/composable-underlay-chaining`, configuration was added to chain `/opt/ros/upstream` as a parent underlay. When `/opt/ros/composable/setup.sh` is sourced, it automatically sources `/opt/ros/upstream/setup.sh`, propagating the entire environment recursively.

### Decision 3: Forking Bloom to Support REP-159 Rules
* **Modifications in `bloom/generators/debian/generator.py`**:
  1. **Binary Name Resolution**: Queries `rosdistro.get_binary_package_name()` to populate `Package:` and `Depends:` in `debian/control`.
  2. **Install Prefix Resolution**: Queries `rosdistro.get_distribution_install_prefix()` to populate `-DCMAKE_INSTALL_PREFIX` in `debian/rules`.
  3. **Chained Underlay Sourcing in `debian/rules`**: Automatically generates sourcing loops in debhelper overrides:
     ```make
     if [ -f "/opt/ros/<parent>/setup.sh" ]; then . "/opt/ros/<parent>/setup.sh"; fi
     ```

---

## 3. Implementation Breakdown: Core Code vs. Testing Tweaks

### Core Implementation (To be Merged Upstream)

1. **`ros2/ros_workspace` (Branch: `feat/composable-underlay-chaining`)**:
   - Adds support for parameterized underlay prefixes in `CMakeLists.txt` and environment hook templates.

2. **`ros-infrastructure/bloom` (Branch: `feat/rep159-rules-support`)**:
   - `bloom/generators/debian/generator.py`: Generates rules-compliant `debian/control` and `debian/rules`.
   - `bloom/generators/debian/templates/rules.em`: Injects parent underlay setup sourcing loops.

3. **`ros-infrastructure/ros_buildfarm` (Branch: `feat/composable-distro`)**:
   - Automatically detects `/opt/ros/<distro>/setup.sh` and prefers native sourcing over synthetic path exports.

### Testing Tweaks & Local Workarounds (Test Harness Only — Do NOT Upstream)

1. **Local Python Environment Overwrite**:
   - Installing bloom via `pip install -e submodules/bloom` pulled `rosdistro` from git, overwriting the local editable `submodules/rosdistro` with a branch that lacked `binary_rule`.
   - *Fix for testing*: Explicitly re-installed the local fork: `pip install -e submodules/rosdistro`.
2. **Dedicated Suite Prefix `C*`**:
   - Jenkins jobs were named with prefix `C*` (`Cci`, `Csrc`, `Cbin`, `Crel_sync`) to clearly isolate Stage 4 runs from earlier test topologies.

---

## 4. Empirical Validation & Test Evidence

### 5-Step Release & CI Pipeline on Local Testfarm (`192.168.30.206`)

1. **Workspace Package Release**:
   - `Csrc_uR__ros_workspace` (#5) & `Cbin_uR64__ros_workspace` (#3): **SUCCESS**. Built `vendor-composable-ros-workspace_1.0.4-1resolute_amd64.deb` under prefix `/opt/ros/composable` and exported to `building`.
2. **Root Distribution Package Release (`composable`)**:
   - `Csrc` & `Cbin` for `upstream_a` (#1, #2), `upstream_b` (#1, #3), `upstream_c` (#1, #3): **SUCCESS**. Built all binary debs (`vendor-composable-upstream-{a,b,c}`) under `/opt/ros/composable`.
3. **Repository Promotion**:
   - `Crel_sync-packages-to-testing_resolute_amd64` (#5): **SUCCESS**. Promoted all 4 debian packages to the local `testing` APT repository.
4. **Native Shell CI Validation**:
   - `Cci__nightly-release_ubuntu_resolute_amd64` (#3): **SUCCESS**. Installed `vendor-composable-ros-workspace` from APT, sourced `. /opt/ros/composable/setup.sh`, compiled `upstream_{a,b,c}` natively, and passed 100% of unit tests.
5. **Downstream Extension Release & CI (`composablebin`)**:
   - `Csrc_uR__downstream_bin_a` (#2) & `Cbin_uR64__downstream_bin_a` (#1): **SUCCESS**. Built `vendor-composablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb`.
   - `Crel_sync-packages-to-testing_resolute_amd64` (#6): **SUCCESS**. Promoted downstream package to `testing`.
   - `Cci__binary-import_ubuntu_resolute_amd64` (#4): **SUCCESS**. Sourced `. /opt/ros/composable/setup.sh` across all build and test phases, compiled `downstream_bin_a` against `vendor-composable-upstream-c`, and passed all CTest/GoogleTest suites 100% green.

---

## 5. Upstream PR & Release Roadmap

1. **PR 1: `ros2/ros_workspace`**
   - *Title*: `feat: support parameterized parent underlays in environment hooks`
   - *Branch*: `feat/composable-underlay-chaining` $\to$ `main`
2. **PR 2: `ros-infrastructure/bloom`**
   - *Title*: `feat(debian): support REP-159 binary_rule, install_rule, and parent underlay sourcing`
   - *Branch*: `feat/rep159-rules-support` $\to$ `master`
   - *Release Target*: `bloom >= 0.15.0`.
