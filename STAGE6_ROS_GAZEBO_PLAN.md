# Stage 6 Plan: Adopting `workspace_package` (`ros_workspace_shell`) & Composable ROS + Gazebo Demonstrations on `build.test.ros2.org`

Architecture, historical progression of workspace chaining across Stages 1–6, stacked branch matrix, and testfarm execution plan for **Stage 6** of the REP-159 validation campaign on `https://build.test.ros2.org`.

---

## 1. Evolution of Workspace Setup & Underlay Chaining (Stages 1 -> 6)

Across our REP-159 testing campaign, we iterated through three distinct mechanisms for managing prefix setup files (`/opt/ros/<distro>/setup.bash`) and parent underlay chaining:

### 1.1 Stages 1–3: Pure CMake Without a Workspace Package (`extendable*`)
* **How We Solved It**:
  - The `extendable`, `extendablesrc`, `extendablebin`, `extendablechain`, `extendablemixed`, and `extendablediamond` distributions contained **only** the pure CMake test packages (`upstream_a/b/c`, `downstream_*`) and **no `ros_workspace` package**.
  - In `bloom`, we conditionally skipped injecting `ros-<distro>-ros-workspace` when `ros_workspace` was absent from the distribution, and passed `-DCMAKE_PREFIX_PATH` directly in `debian/rules.em` while guarding `. "/opt/ros/<parent>/setup.sh"` behind `if [ -f ... ]`.
  - In `ros_buildfarm` (`workspace.py`), when `/opt/ros/<parent>/setup.sh` did not exist on disk, the buildfarm read `ROS_BUILDFARM_PARENT_RESULT_SPACES` and directly exported `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, `LD_LIBRARY_PATH`, and `PATH`.
* **What It Validated vs. Its Limitation**:
  - Validated `binary_rule` regex renaming, `install_rule` custom prefixes (`/opt/vendor/extendable`), `ReleaseAndSourceDependencyWalker` boundary pruning, and 3-tier/hybrid/diamond DAG traversal with zero bootstrap packages.
  - **Limitation**: Installed `.deb` packages did not place `/opt/ros/<distro>/setup.bash` on disk, so end users installing the binaries in a container had to export `LD_LIBRARY_PATH` and `CMAKE_PREFIX_PATH` manually.

### 1.2 Stages 4–5: Full `ros_workspace` + `ament_cmake` Stack (`extendable` & `extendablebin`)
* **How We Solved It**:
  - To provide end users with `/opt/ros/<distro>/setup.bash` and automatic parent underlay chaining, we adopted Jose Luis Rivero's (`jrivero`) `BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])` in `rosdistro`, `ROS_WORKSPACE_PARENT_PREFIX_PATH` in `ros_workspace`, and `ParentPrefixes` in `bloom`.
  - In the root distribution (`extendable`), we bloomed and built **all 3 Ament bootstrap packages** (`ament_package`, `ament_cmake_core`, and `ros_workspace`), and carried the manual `export PYTHONPATH=...` bootstrap patch in `ament_cmake_core-release` so `ament_cmake_core` could find `ament_package` before `ros_workspace` existed.
  - In the `binary_import` child (`extendablebin`), we released a child `ros_workspace` package that chained `/opt/ros/extendable` via `-DROS_WORKSPACE_PARENT_PREFIX_PATH="/opt/ros/extendable"`.
* **What It Validated vs. Its Limitation**:
  - Validated full ROS 2 `setup.bash` recursive underlay chaining, automated `bloom` Debian generation, and `rosdistro_build_cache` parent cache merging (`extendable_rosdistro-cache`, `extendablebin_rosdistro-cache`).
  - **Limitation**: Any root or `source_rebuild` distribution (even a pure CMake or Gazebo distribution) was forced to bloom and build 3 Ament packages (`ament_package`, `ament_cmake_core`, `ros_workspace`) and maintain a manual `debian/rules` patch in `ament_cmake_core-release`.

### 1.3 Stage 6+: Adopting Jose Luis Rivero's `ros_workspace_shell` Split & `workspace_package` Key
* **Why We Adopt Jose's Solution for Stage 6+**:
  - Jose split the prefix setup scripts out of `ros_workspace` into [`rep159-testing/ros_workspace_shell`](https://github.com/rep159-testing/ros_workspace_shell) (`a89cc7b`, tag `0.1.0`), a **plain CMake** package with **zero Ament dependencies** (depends only on `python3`), and introduced the optional v3 `distribution.yaml` top-level key `workspace_package`.
  - When a non-ROS / Gazebo / CMake distribution sets `workspace_package: ros_workspace_shell`:
    1. Only **1 tiny plain-CMake bootstrap package** (`ros_workspace_shell`) is needed instead of 3 Ament packages.
    2. **Zero manual `debian/rules` patches** are needed (no `ament_cmake_core` bootstrap cycle).
    3. Every distribution still installs `/opt/ros/<distro>/setup.sh`, `setup.bash`, `setup.zsh`, `local_setup.*`, and `.dsv` hooks, and chains parent prefixes via `-DROS_WORKSPACE_PARENT_PREFIX_PATH`.
    4. A ROS 2 child distribution (using default `ros_workspace` or `ros_workspace_shell`) automatically depends on and chains each parent's own configured `workspace_package` (`get_binary_import_parent_workspace_packages`).

### 1.4 Comparison Summary Across Stages 1–6

| Aspect | Stages 1–3 (Pure CMake, No Workspace Pkg) | Stages 4–5 (Full `ros_workspace`) | Stage 6+ (Adopted `workspace_package` / `ros_workspace_shell`) |
| :--- | :--- | :--- | :--- |
| **Bootstrap packages in Root / `source_rebuild` non-ROS distro** | **0** | **3** (`ament_package`, `ament_cmake_core`, `ros_workspace`) | **1** (`ros_workspace_shell` — plain CMake, no Ament) |
| **Bootstrap packages in `binary_import` child distro** | **0** | **1** (`ros_workspace`) | **1** (`ros_workspace` for ROS 2 child, or `ros_workspace_shell` for CMake child) |
| **Manual `PYTHONPATH` patch in `ament_cmake_core-release`?** | No | **Yes** | **No** |
| **Installs `/opt/ros/<distro>/setup.bash` for end users?** | **No** | **Yes** | **Yes** |
| **Recursive runtime underlay chaining (`parent_prefix_path`)?** | No (buildfarm env export only) | **Yes** | **Yes** (works across mixed `ros_workspace` and `ros_workspace_shell` layers) |
| **Supports `binary_rule`, `install_rule`, & `distribution_eol_date`?** | **Yes** | **Yes** | **Yes** (unified on `feat/rep159-workspace-package`) |

---

## 2. Strict Collaborator & Testfarm Isolation Guarantee

All Stage 6 work strictly obeys the following non-overlap rules:
1. **Collaborator Branches Untouched**: Jose's branches (`rep159`, `rep159-workspace-package`, `rep159-shell`, `rep159-setup-chain`, `rep159-child-ros-workspace`, `rep159-parent-chain`, `rep159-split-base`, `kmom88`) are never modified or force-pushed.
2. **Stage 1–5 Branches Untouched**: All of our existing Stage 1–5 `feat/*` branches remain frozen at their verified commits.
3. **Collaborator Distributions & Jenkins Jobs Untouched**: Jose's distributions (`upstream`, `srcext`, `binext`, `ground`, `derived`) and Jenkins jobs (`U*`, `S*`, `B*`, `G*`, `D*`, as well as `C*`) are never modified or triggered. All our testfarm jobs stay strictly in the **`extendable*` (`E*`)** namespace.

---

## 3. Stacked Branch Matrix for Stage 6 (`feat/rep159-workspace-package`)

We have stacked Jose's `workspace_package` commits directly on top of our Stage 5 / `eol-date` stack:

| Submodule / Repository | Base Branch (Untouched) | New Stacked Branch (`@ SHA`) | Adopted `jrivero` Commit & Unified Features | Unit Tests |
| :--- | :--- | :--- | :--- | :---: |
| **[submodules/rosdistro](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/rosdistro)** | `feat/rep159-eol-date` (`5ec62f9`)<br>*(on `feat/rep159-install-rule` `a8f5543`)* | [`feat/rep159-workspace-package`](https://github.com/rep159-testing/rosdistro/tree/feat/rep159-workspace-package) (`3670bd8`) | Cherry-picks `bc0600f` (`Jose Luis Rivero`): parses `workspace_package` in v3 `distribution.yaml`, sets `binary_import_overridable = frozenset([self.workspace_package or 'ros_workspace'])`, and normalizes hyphenated package names (`pkg_name.replace('-', '_')`) in `get_binary_package_name()` and `get_install_prefix()`. | **106 / 106 PASS** |
| **[submodules/bloom](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/bloom)** | `feat/rep159-rules-support` (`7af7034`) | [`feat/rep159-workspace-package`](https://github.com/rep159-testing/bloom/tree/feat/rep159-workspace-package) (`ec0bcca`) | Cherry-picks `2cb93dc` (`Jose Luis Rivero`): `get_workspace_package()`, `get_binary_import_parent_workspace_packages()`, and `get_workspace_dependencies()`, resolves parent `extends` in `get_distribution_file()`, and unsets `AMENT_CURRENT_PREFIX` after each parent `setup.sh` in `debian/rules.em`. | **37 / 37 PASS** |
| **[submodules/ros_buildfarm](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/ros_buildfarm)** *(Clean PR)* | `feat/rep159-binary-naming` (`a271be1`) | [`feat/rep159-workspace-package`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/rep159-workspace-package) (`e54594c`) | Cherry-picks `146d05f` (`Jose Luis Rivero`): `_get_and_parse_distribution_cache` in `release_job.py` uses `get_workspace_package(dist_cache.distribution_file)`. Zero Dockerfile pip hacks. | **27 / 27 PASS** |
| **[submodules/ros_buildfarm](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/ros_buildfarm)** *(Testbed)* | `feat/extendable-workspace` (`ca13954`) | [`feat/extendable-workspace-package`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/extendable-workspace-package) (`b242685`) | Cherry-picks `146d05f` (`3f127b7`), pins `rosdistro` `3670bd8` across task Dockerfile templates, supports `ext*` release build prefixes inside `Esrc_uR` and `Ebin_uR64`, exports `CMAKE_PREFIX_PATH` in `workspace.py` for `parent_result_spaces` with `setup.sh`, and unsets `AMENT_CURRENT_PREFIX` between chained `setup.sh` calls (`b242685`). | **33 / 33 PASS** |
| **[submodules/reps](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/reps)** | `feature/rep-159-install-rule` (`1aef980`) | [`feature/rep-159-workspace-package`](https://github.com/KmoM88/reps/tree/feature/rep-159-workspace-package) (`0905caa`) | Documents `workspace_package` (`ros_workspace_shell` vs `ros_workspace`) in Distribution File v3 and `distribution_eol_date` in Index File v4 (`openrobotics/reps#37`). | Spec Verified |
| **[submodules/rosdistro-reviewer](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/rosdistro-reviewer)** | `main` (`6e2a173`) | [`feat/rep159-eol-date`](https://github.com/rep159-testing/rosdistro-reviewer/tree/feat/rep159-eol-date) (`3e6ab56`) | Implements `_check_eol_dates` in `RosdistroAnalyzer` validating `distribution_eol_date` ISO 8601 format (`YYYY-MM-DD` / `YYYY-MM`) and detecting parent/child EOL mismatches (`parent_eol < child_eol`) across `extends`. | **200 / 200 PASS** |
| **[submodules/rep159-rosdistro](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/rep159-rosdistro)** | `feat/extendable-workspace` (`19aedba`) | [`feat/extendable-gazebo`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/extendable-gazebo) (`f3891ce`) | Adds `lyrical` (156-package ROS 2 Lyrical parent subset), `extendablejetty` (6-package Gazebo root with `workspace_package: ros_workspace_shell`), `extendablelyricalsrc` (`source_rebuild`), and multi-parent `extendablelyrical` (`extends: [lyrical, extendablejetty]`, `ros_workspace`, `gz-demo-math`, `ros_gz_interfaces`, vendorless `ros_gz_bridge`). | Cache Verified |
| **[submodules/ros_buildfarm_config](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/ros_buildfarm_config)** | `feat/extendable-workspace` (`c80b6f7`) | [`feat/extendable-gazebo`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/extendable-gazebo) (`5bdad6b`) | Adds `extendablejetty` (`extjetty`), `extendablelyricalsrc`, and `extendablelyrical` (`extlyrical`) CI and release build configs under `E*`. | Dry-Run & Live Jobs Generated |
| **[submodules/ros_workspace_shell](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/ros_workspace_shell)** | `main` (`a89cc7b`, tag `0.1.0`) | [`feat/rep159-unset-current-prefix`](https://github.com/rep159-testing/ros_workspace_shell/tree/feat/rep159-unset-current-prefix) (`b6a8195`) | Jose's plain-CMake prefix setup package (`ros_workspace_shell`), plus `unset AMENT_CURRENT_PREFIX` after sourcing `local_setup.sh` in `templates/prefix_level/setup.sh.in`. | Verified |
| **[submodules/gz-tools](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/gz-tools)** | `gz-tools2` (`2.0.3`) | [`feat/rep159-jetty`](https://github.com/rep159-testing/gz-tools/tree/feat/rep159-jetty) (`a55273d`) | Adds `package.xml` (`gz-tools2` `2.0.3`, `<build_type>cmake</build_type>`) for Gazebo Jetty (`rep159-testing/gz-tools2-release.git`). | Verified |
| **[submodules/gz-transport](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/gz-transport)** | `gz-transport15` (`15.0.1`) | [`feat/rep159-jetty`](https://github.com/rep159-testing/gz-transport/tree/feat/rep159-jetty) (`7516752f`) | Adds `package.xml` (`gz-transport` `15.0.1`, `<build_type>cmake</build_type>`) for Gazebo Jetty (`rep159-testing/gz-transport-release.git`). | Verified |
| **[submodules/ros_gz](file:///usr/local/google/home/rossif/github/kmom88/rep159-testing/submodules/ros_gz)** | `ros2` (`3.0.12`) | [`feat/rep159-no-vendor`](https://github.com/rep159-testing/ros_gz/tree/feat/rep159-no-vendor) (`efec554`) | Removes `gz_msgs_vendor` and `gz_transport_vendor` from `ros_gz_bridge/package.xml` and `CMakeLists.txt`, calling `find_package(gz-msgs12 REQUIRED)` and `find_package(gz-transport15 REQUIRED)` directly against the `extendablejetty` underlay (`rep159-testing/ros_gz-release.git`). | Verified |

---

## 4. Stage 6 Execution Plan (Aligned with Nov 11 Coordination Notes)

### Phase 6A: Tooling Stack Unification (`feat/rep159-workspace-package`) — COMPLETED
- Stacked `feat/rep159-workspace-package` across `rosdistro` (`5d4a392`), `bloom` (`aa5133e`), `ros_buildfarm` (`e54594c` clean / `2bff39e` testbed), and `reps` (`0905caa`).
- Added `submodules/ros_workspace_shell` and `submodules/ros_workspace_shell-release` to `.gitmodules`.

### Phase 6B: Demonstration 1 — Import Gazebo into ROS (`lyrical`/`jetty` & `rolling`/`rotary`, Up to `ros_gz_bridge` Without Vendor Packages)
```mermaid
flowchart TD
    subgraph GazeboBase ["Root Gazebo Distro: extendablejetty / extendablerotary (Jobs E*)"]
        GZ["Prefix: /opt/ros/extendablejetty (or /opt/ros/extendablerotary)<br/>workspace_package: ros_workspace_shell (Zero Ament packages)<br/>Step 1 (Minimal): ros_workspace_shell, gz-cmake, gz-utils, gz-math<br/>Step 2 (Full Bridge): + gz-tools, gz-msgs, gz-transport"]
    end

    subgraph RosChildBin ["Child ROS 2 Distro (binary_import): extendablelyrical / extendablerolling (Jobs E*)"]
        ROS_BIN["extends: extendablejetty / extendablerotary (binary_import)<br/>Prefix: /opt/ros/extendablelyrical (or /opt/ros/extendablerolling)<br/>workspace_package: ros_workspace (or ros_workspace_shell)<br/>Step 1 (Minimal): gz-demo-math<br/>Step 2 (Full Bridge): ros_gz_interfaces, vendorless ros_gz_bridge"]
    end

    subgraph RosChildSrc ["Child ROS 2 Distro (source_rebuild): extendablerollingsrc (Jobs E*)"]
        ROS_SRC["extends: extendablerotary (source_rebuild)<br/>Rebuilds Gazebo chain + consumer in single prefix"]
    end

    GZ -->|"binary_import + ROS_WORKSPACE_PARENT_PREFIX_PATH"| ROS_BIN
    GZ -->|"source_rebuild"| ROS_SRC
```

1. **Step 6B-1 (Gazebo `ros_workspace_shell` + `gz-demo-math` Smoke Test in `E*`) — COMPLETED (17/17 `SUCCESS`)**:
   - Configured `extendablejetty` (root Gazebo distribution with `workspace_package: ros_workspace_shell`, `gz-cmake` `5.1.1-1`, `gz-utils` `4.0.0-1`, `gz-math` `9.3.0-1` — **zero Ament packages**), `extendablelyricalsrc` (`source_rebuild` child), and `extendablelyrical` (`binary_import` child with `ros_workspace_shell` `0.1.0-1` chaining `/opt/ros/extendablejetty` + `gz-demo-math` `1.0.1-1`).
   - Added permanent stage and Bloom orchestration tools in [`tools/stage_runner.py`](tools/stage_runner.py) and [`tools/bloom_stage6_gazebo.py`](tools/bloom_stage6_gazebo.py).
   - Executed all 17 `E*` release, sync, and CI jobs on `https://build.test.ros2.org` (**17 / 17 `SUCCESS`**):
     - `Esrc_uR__extjetty_ros_workspace_shell__ubuntu_resolute__source` [#1](https://build.test.ros2.org/job/Esrc_uR__extjetty_ros_workspace_shell__ubuntu_resolute__source/1/) — **SUCCESS**
     - `Esrc_uR__extjetty_gz-cmake__ubuntu_resolute__source` [#1](https://build.test.ros2.org/job/Esrc_uR__extjetty_gz-cmake__ubuntu_resolute__source/1/) — **SUCCESS**
     - `Esrc_uR__extjetty_gz-utils__ubuntu_resolute__source` [#1](https://build.test.ros2.org/job/Esrc_uR__extjetty_gz-utils__ubuntu_resolute__source/1/) — **SUCCESS**
     - `Esrc_uR__extjetty_gz-math__ubuntu_resolute__source` [#1](https://build.test.ros2.org/job/Esrc_uR__extjetty_gz-math__ubuntu_resolute__source/1/) — **SUCCESS**
     - `Esrc_uR__extlyrical_ros_workspace_shell__ubuntu_resolute__source` [#1](https://build.test.ros2.org/job/Esrc_uR__extlyrical_ros_workspace_shell__ubuntu_resolute__source/1/) — **SUCCESS**
     - `Esrc_uR__extlyrical_gz-demo-math__ubuntu_resolute__source` [#1](https://build.test.ros2.org/job/Esrc_uR__extlyrical_gz-demo-math__ubuntu_resolute__source/1/) — **SUCCESS**
     - `Ebin_uR64__extjetty_ros_workspace_shell__ubuntu_resolute_amd64__binary` [#1](https://build.test.ros2.org/job/Ebin_uR64__extjetty_ros_workspace_shell__ubuntu_resolute_amd64__binary/1/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-cmake__ubuntu_resolute_amd64__binary` [#2](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-cmake__ubuntu_resolute_amd64__binary/2/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-utils__ubuntu_resolute_amd64__binary` [#2](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-utils__ubuntu_resolute_amd64__binary/2/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-math__ubuntu_resolute_amd64__binary` [#2](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-math__ubuntu_resolute_amd64__binary/2/) — **SUCCESS**
     - `Erel_extjetty_sync-packages-to-testing_resolute_amd64` [#2](https://build.test.ros2.org/job/Erel_extjetty_sync-packages-to-testing_resolute_amd64/2/) — **SUCCESS**
     - `Ebin_uR64__extlyrical_ros_workspace_shell__ubuntu_resolute_amd64__binary` [#2](https://build.test.ros2.org/job/Ebin_uR64__extlyrical_ros_workspace_shell__ubuntu_resolute_amd64__binary/2/) — **SUCCESS**
     - `Ebin_uR64__extlyrical_gz-demo-math__ubuntu_resolute_amd64__binary` [#3](https://build.test.ros2.org/job/Ebin_uR64__extlyrical_gz-demo-math__ubuntu_resolute_amd64__binary/3/) — **SUCCESS**
     - `Erel_extlyrical_sync-packages-to-testing_resolute_amd64` [#2](https://build.test.ros2.org/job/Erel_extlyrical_sync-packages-to-testing_resolute_amd64/2/) — **SUCCESS**
     - `Eci__gazebo-jetty-release_ubuntu_resolute_amd64` [#1](https://build.test.ros2.org/job/Eci__gazebo-jetty-release_ubuntu_resolute_amd64/1/) — **SUCCESS**
     - `Eci__gazebo-lyrical-source-rebuild_ubuntu_resolute_amd64` [#1](https://build.test.ros2.org/job/Eci__gazebo-lyrical-source-rebuild_ubuntu_resolute_amd64/1/) — **SUCCESS**
     - `Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64` [#2](https://build.test.ros2.org/job/Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64/2/) — **SUCCESS**
2. **Step 6B-2a (Single-Parent Full 6-Package Gazebo `extendablejetty` -> `extendablelyrical` / `extendablelyricalsrc`) — COMPLETED (23/23 `SUCCESS`)**:
   - Expanded `extendablejetty` to all 6 Gazebo Jetty packages (`gz-cmake` `5.1.1-1`, `gz-utils` `4.0.0-1`, `gz-math` `9.3.0-1`, `gz-tools2` `2.0.3-1`, `gz-msgs` `12.0.2-1`, `gz-transport` `15.0.1-1`) + `ros_workspace_shell` (`0.1.0-1`), all hosted in `rep159-testing/*-release.git` repositories with zero personal repo URLs.
   - Executed all 23 `E*` release, sync, and CI jobs on `https://build.test.ros2.org` (**23 / 23 `SUCCESS`**):
     - `Esrc_uR__extjetty_{ros_workspace_shell,gz-cmake,gz-utils,gz-math,gz-tools2,gz-msgs,gz-transport}__ubuntu_resolute__source` — **SUCCESS**
     - `Ebin_uR64__extjetty_{ros_workspace_shell,gz-cmake,gz-utils,gz-math,gz-tools2,gz-msgs,gz-transport}__ubuntu_resolute_amd64__binary` — **SUCCESS**
     - `Erel_extjetty_sync-packages-to-testing_resolute_amd64` [#4](https://build.test.ros2.org/job/Erel_extjetty_sync-packages-to-testing_resolute_amd64/4/) — **SUCCESS**
     - `Esrc_uR__extlyrical_{ros_workspace_shell,gz-demo-math}__ubuntu_resolute__source` & `Ebin_uR64__extlyrical_{ros_workspace_shell,gz-demo-math}__ubuntu_resolute_amd64__binary` — **SUCCESS**
     - `Erel_extlyrical_sync-packages-to-testing_resolute_amd64` [#3](https://build.test.ros2.org/job/Erel_extlyrical_sync-packages-to-testing_resolute_amd64/3/) — **SUCCESS**
     - `Eci__gazebo-jetty-release_ubuntu_resolute_amd64` [#2](https://build.test.ros2.org/job/Eci__gazebo-jetty-release_ubuntu_resolute_amd64/2/) — **SUCCESS**
     - `Eci__gazebo-lyrical-source-rebuild_ubuntu_resolute_amd64` [#2](https://build.test.ros2.org/job/Eci__gazebo-lyrical-source-rebuild_ubuntu_resolute_amd64/2/) — **SUCCESS**
     - `Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64` [#3](https://build.test.ros2.org/job/Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64/3/) — **SUCCESS**
3. **Step 6B-2b (Multi-Parent `extends: [lyrical, extendablejetty]` + Vendorless `ros_gz_bridge`) — COMPLETED (18/18 `SUCCESS`)**:
   - Configured `extendablelyrical` to extend `[lyrical, extendablejetty]` via `binary_import` using standard `ros_workspace` (`1.0.4-1`, chaining both `ros-lyrical-ros-workspace` `/opt/ros/lyrical` and `ros-extendablejetty-ros-workspace-shell` `/opt/ros/extendablejetty`), `gz-demo-math` (`1.0.1-1`), `ros_gz_interfaces` (`3.0.12-1`), and vendorless `ros_gz_bridge` (`3.0.12-1`, consuming `gz-msgs` and `gz-transport` directly from `/opt/ros/extendablejetty` without `gz_msgs_vendor` or `gz_transport_vendor`).
   - Fixed POSIX `/bin/sh` `AMENT_CURRENT_PREFIX` leaking across chained `setup.sh` scripts in `bloom` (`rules.em`), `ros_buildfarm` (`workspace.py`), and `ros_workspace_shell` (`setup.sh.in`).
   - Executed all 18 `E*` release, sync, and CI jobs in `stage6-gazebo-step2b` on `https://build.test.ros2.org` (**18 / 18 `SUCCESS`**):
     - `Esrc_uR__extjetty_ros_workspace_shell__ubuntu_resolute__source` [#2](https://build.test.ros2.org/job/Esrc_uR__extjetty_ros_workspace_shell__ubuntu_resolute__source/2/) — **SUCCESS**
     - `Esrc_uR__extlyrical_ros_workspace__ubuntu_resolute__source` [#2](https://build.test.ros2.org/job/Esrc_uR__extlyrical_ros_workspace__ubuntu_resolute__source/2/) — **SUCCESS**
     - `Esrc_uR__extlyrical_gz-demo-math__ubuntu_resolute__source` [#3](https://build.test.ros2.org/job/Esrc_uR__extlyrical_gz-demo-math__ubuntu_resolute__source/3/) — **SUCCESS**
     - `Esrc_uR__extlyrical_ros_gz_interfaces__ubuntu_resolute__source` [#2](https://build.test.ros2.org/job/Esrc_uR__extlyrical_ros_gz_interfaces__ubuntu_resolute__source/2/) — **SUCCESS**
     - `Esrc_uR__extlyrical_ros_gz_bridge__ubuntu_resolute__source` [#2](https://build.test.ros2.org/job/Esrc_uR__extlyrical_ros_gz_bridge__ubuntu_resolute__source/2/) — **SUCCESS**
     - `Ebin_uR64__extjetty_ros_workspace_shell__ubuntu_resolute_amd64__binary` [#2](https://build.test.ros2.org/job/Ebin_uR64__extjetty_ros_workspace_shell__ubuntu_resolute_amd64__binary/2/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-cmake__ubuntu_resolute_amd64__binary` [#3](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-cmake__ubuntu_resolute_amd64__binary/3/) — **SUCCESS**
     - `Ebin_uR64__extlyrical_ros_workspace__ubuntu_resolute_amd64__binary` [#4](https://build.test.ros2.org/job/Ebin_uR64__extlyrical_ros_workspace__ubuntu_resolute_amd64__binary/4/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-utils__ubuntu_resolute_amd64__binary` [#3](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-utils__ubuntu_resolute_amd64__binary/3/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-tools2__ubuntu_resolute_amd64__binary` [#2](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-tools2__ubuntu_resolute_amd64__binary/2/) — **SUCCESS**
     - `Ebin_uR64__extlyrical_ros_gz_interfaces__ubuntu_resolute_amd64__binary` [#4](https://build.test.ros2.org/job/Ebin_uR64__extlyrical_ros_gz_interfaces__ubuntu_resolute_amd64__binary/4/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-math__ubuntu_resolute_amd64__binary` [#3](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-math__ubuntu_resolute_amd64__binary/3/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-msgs__ubuntu_resolute_amd64__binary` [#3](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-msgs__ubuntu_resolute_amd64__binary/3/) — **SUCCESS**
     - `Ebin_uR64__extlyrical_gz-demo-math__ubuntu_resolute_amd64__binary` [#9](https://build.test.ros2.org/job/Ebin_uR64__extlyrical_gz-demo-math__ubuntu_resolute_amd64__binary/9/) — **SUCCESS**
     - `Ebin_uR64__extjetty_gz-transport__ubuntu_resolute_amd64__binary` [#4](https://build.test.ros2.org/job/Ebin_uR64__extjetty_gz-transport__ubuntu_resolute_amd64__binary/4/) — **SUCCESS**
     - `Erel_extjetty_sync-packages-to-testing_resolute_amd64` [#7](https://build.test.ros2.org/job/Erel_extjetty_sync-packages-to-testing_resolute_amd64/7/) — **SUCCESS**
     - `Ebin_uR64__extlyrical_ros_gz_bridge__ubuntu_resolute_amd64__binary` [#3](https://build.test.ros2.org/job/Ebin_uR64__extlyrical_ros_gz_bridge__ubuntu_resolute_amd64__binary/3/) — **SUCCESS**
     - `Erel_extlyrical_sync-packages-to-testing_resolute_amd64` [#6](https://build.test.ros2.org/job/Erel_extlyrical_sync-packages-to-testing_resolute_amd64/6/) — **SUCCESS**
     - `Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64` [#6](https://build.test.ros2.org/job/Eci__gazebo-lyrical-binary-import_ubuntu_resolute_amd64/6/) — **SUCCESS** (7/7 C++ GoogleTest suites & 37/37 xunit tests passing)

### Phase 6C: Demonstration 2 — 3rd-Party Extension of a ROS 2 Distribution
- Define a 3rd-party child distribution (`extendable3rdparty`, Jenkins jobs `E*`) extending a ROS 2 base distribution (`source_rebuild` and same-buildfarm `binary_import` on `build.test.ros2.org`) and building a downstream 3rd-party ROS 2 package without rebuilding the parent ROS 2 packages in `binary_import` mode.

### Phase 6D: `distribution_eol_date` Check in `rosdistro-reviewer` — COMPLETED (200/200 `PASS`)
- Forked `ros-infrastructure/rosdistro-reviewer` to [`rep159-testing/rosdistro-reviewer`](https://github.com/rep159-testing/rosdistro-reviewer), registered `submodules/rosdistro-reviewer`, and implemented `_parse_eol_date` and `_check_eol_dates` on branch [`feat/rep159-eol-date`](https://github.com/rep159-testing/rosdistro-reviewer/tree/feat/rep159-eol-date) (`3e6ab56`):
  1. Validates `distribution_eol_date` (`YYYY-MM-DD` and `YYYY-MM`) in `index-v4.yaml` and emits a recommendation when malformed or missing on active distributions.
  2. Detects **Parent/Child EOL mismatches** (`parent_eol < child_eol`) when a child distribution `extends` a parent distribution whose `distribution_eol_date` expires before the child's `distribution_eol_date`.
  3. All **200 / 200** unit and linter tests (`flake8`, `mypy`, `scspell3k`, `copyright_license`, `yamllint`) pass.
