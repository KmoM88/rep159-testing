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

## 3. Implementation Breakdown: Core Code vs. Required Fixes vs. Testing Tweaks

### Core Feature Implementation (To Be Merged Upstream)

1. **`ros2/ros_workspace` (`rep159-parent-chain` @ `12f93e9` & `feat/composable-underlay-chaining` @ `032d161`)**:
   - Parameterizes `ROS_WORKSPACE_PARENT_PREFIX_PATH` / `PARENT_PREFIX_PATH` in `CMakeLists.txt` so extended distribution builds of `ros_workspace` register parent underlay prefixes into the `parent_prefix_path` ament resource index and locate `ament_package` across parent underlays.

2. **`ros-infrastructure/bloom` (`feat/rep159-rules-support` @ `d6fdf9e` stacked on `rep159` @ `2877687`)**:
   - `bloom/rosdistro_api.py`: Implements `get_binary_import_parents()`, `get_ros_workspace_dependencies()`, `get_binary_package_name()`, and `get_install_prefix()`.
   - `bloom/generators/rosdebian.py`: Parameterizes `InstallationPrefix`, `ParentPrefixes`, and `rosify_package_name()` (`Package:` and `Depends:`) using `install_rule` and `binary_rule`.
   - `bloom/generators/debian/templates/{ament_cmake,cmake}/rules.em`: Injects parent `<prefix>/setup.sh` sourcing loops, chains `CMAKE_PREFIX_PATH` & `PKG_CONFIG_PATH`, and passes `-DROS_WORKSPACE_PARENT_PREFIX_PATH=...`.

3. **`ros-infrastructure/ros_buildfarm` (`feat/binary-naming-rule` @ `4062a66`)**:
   - `ros_buildfarm/workspace.py`: Automatically sources `<prefix>/setup.sh` when present on disk (`vendor-composable-ros-workspace`) while retaining pure-CMake environment exports as a fallback.

### Required Engineering Fixes Before Creating Upstream PRs

1. **`ros_workspace` Branch Reconciliation (`12f93e9` + `032d161`)**:
   - Combine `rep159-parent-chain` (`12f93e9` — multi-prefix search for `ament_package` across `ROS_WORKSPACE_PARENT_PREFIX_PATH` and preserving default `SKIP_PARENT_PREFIX_PATH` when no parent prefix is passed) with `feat/composable-underlay-chaining` (`032d161` — `PARENT_PREFIX_PATH` alias and explicit `ament_index_register_resource("parent_prefix_path" ...)`).
2. **`bloom` Regex Dictionary `install_rule` Fix (`bloom/rosdistro_api.py:get_install_prefix()`)**:
   - Lines 269–270 currently call `dist_file.install_rule.replace('{distro}', distro)`, which fails with `AttributeError` (silently falling back to `/opt/ros/<distro>`) when `install_rule` is a regex `dict` (`{'search': ..., 'replace': ...}`). Update `get_install_prefix()` to delegate directly to `dist_file.get_install_prefix()`.
3. **`bloom` Version Pins (Post-Gates 1 & 2)**:
   - Bump `rosdistro >= 1.2.0` and `rosdep >= 0.27.0` in `setup.py` and `stdeb.cfg`.

### Testing Tweaks & Local Workarounds (Test Harness Only — Do NOT Upstream)

1. **Local Python Environment Overwrite**:
   - Installing bloom via `pip install -e submodules/bloom` pulled `rosdistro` from PyPI/git, overwriting the local editable `submodules/rosdistro` before Gate 1 existed.
   - *Fix for testing*: Explicitly re-installed the local fork (`pip install -e submodules/rosdistro`). Solved permanently once Gate 1 (`rosdistro >= 1.2.0`) is published to PyPI.
2. **Dedicated Suite Prefix `C*` & `*-local.yaml` Configs**:
   - Jenkins jobs were named with prefix `C*` (`Cci`, `Csrc`, `Cbin`, `Crel_sync`) using `composable/*-local.yaml` pointing to the local mirror (`192.168.30.202:8088`).

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

## 5. Release-Gated Upstream PR & Release Sequence

1. **Wave 1 — `ros2/ros_workspace` (Independent CMake PR; Packaging Child `.deb` Requires Gate 3)**:
   - *Title*: `feat: support parent underlay prefix chaining and parent ament_package discovery for REP-159`
   - *Source Branches*: Reconciled `rep159-parent-chain` (`12f93e9`) + `feat/composable-underlay-chaining` (`032d161`) $\to$ `main`.
   - *Unblocks Release Gate 2B*: **`ros_workspace >= 1.0.4`**.
2. **Wave 2 — `ros-infrastructure/bloom` (Blocked Until Gate 1 `rosdistro >= 1.2.0` + Gate 2 `rosdep >= 0.27.0`)**:
   - *Title*: `feat(debian): support REP-159 binary_rule, install_rule, and parent underlay chaining`
   - *Source Branches*: `rep159` (`0189046`..`2877687`) + `feat/rep159-rules-support` (`1f62809`, `d6fdf9e`) + `get_install_prefix()` dict delegation fix + `setup.py`/`stdeb.cfg` dependency bumps $\to$ `master` (org base: `rep159`).
   - *Unblocks Release Gate 3*: **`bloom >= 0.15.0`** (PyPI + `ros_bootstrap` APT).
