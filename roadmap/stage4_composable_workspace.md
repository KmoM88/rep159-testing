# Stage 4: `extendable` & `extendablebin` (`E*`) — Native `ros_workspace` Sourcing & Bloom Integration

## 1. Executive Summary & Problem Statement

- **Stages 1–3 (`extendable*` family, Jenkins jobs `E*`)**: Validated pure graph traversal, custom binary naming (`binary_rule`), and installation prefixes (`install_rule`) using pure CMake packages with buildfarm-injected environment fallbacks (`CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`).
- **Stage 4 (`extendable` & `extendablebin`, Jenkins jobs `E*`)**: Evolves `extendable*` (`E*`) onto the native ROS 2 runtime stack by packaging `ament_package`, `ament_cmake_core`, and `ros_workspace` (`/opt/ros/<distro>/setup.sh`, `.dsv` hooks, `AMENT_PREFIX_PATH`), verifying recursive bash underlay chaining (`ROS_WORKSPACE_PARENT_PREFIX_PATH`), and automating Debian packaging via `bloom`.

---

## 2. Design Decisions & Technical Rationale

| Decision | Mechanism | Verified Invariant on `build.test.ros2.org` |
|---|---|---|
| **1. Native Setup Sourcing (`ros_workspace`)** | Package `ros_workspace` as `vendor-extendable-ros-workspace` (`/opt/ros/extendable`) and `vendor-extendablebin-ros-workspace` (`/opt/ros/extendablebin`). | Buildfarm CI and release jobs detect `/opt/ros/<distro>/setup.sh` and execute build/test steps inside that native shell environment. |
| **2. Child `ros_workspace` Override (`rosdistro`)** | `BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])` (`aefe17c`, `a8f5543`). | Allows `extendablebin` (`binary_import`) to release its own `ros_workspace` while keeping all other inherited parent packages immutable. |
| **3. Underlay Chaining (`ROS_WORKSPACE_PARENT_PREFIX_PATH`)** | `ros_workspace` (`12f93e9` + `4997f85`) discovers `ament_package` across `${CMAKE_INSTALL_PREFIX};${ROS_WORKSPACE_PARENT_PREFIX_PATH}` and writes the `parent_prefix_path` ament index. | Sourcing `/opt/ros/extendablebin/setup.sh` automatically chains `/opt/ros/extendable/local_setup.sh`. |
| **4. Automated `bloom` Packaging** | `bloom` (`0189046`..`2877687` + `7af7034`) evaluates `get_binary_package_name()`, `get_install_prefix()`, and `get_binary_import_parents()`. | `git-bloom-generate rosdebian` generates `debian/control` (`Package: vendor-extendablebin-downstream-bin-a`) and `debian/rules` (`ParentPrefixes` sourcing loop). |

---

## 3. Implementation Breakdown: Clean Branches vs. Testbed Branches

| Repository | Clean Upstream PR Branch (`@ SHA`) | Testfarm Branch (`@ SHA`) | Summary |
|---|---|---|---|
| **`ros-infrastructure/rosdistro`** | [`feat/rep159-install-rule`](https://github.com/rep159-testing/rosdistro/tree/feat/rep159-install-rule) (`a8f5543`) | `feat/rep159-install-rule` (`a8f5543`) | Adopts `jrivero`'s `BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])` (`aefe17c`, `a8f5543`) + `binary_rule` & `install_rule` (96/96 tests). |
| **`ros2/ros_workspace`** | [`feat/rep159-parent-chaining`](https://github.com/rep159-testing/ros_workspace/tree/feat/rep159-parent-chaining) (`4997f85`) | `feat/rep159-parent-chaining` (`4997f85`) | Stacked directly on `jrivero`'s `12f93e9` (`ROS_WORKSPACE_PARENT_PREFIX_PATH` & `parent_prefix_path` index) + `PARENT_PREFIX_PATH` alias. |
| **`ros-infrastructure/bloom`** | [`feat/rep159-rules-support`](https://github.com/rep159-testing/bloom/tree/feat/rep159-rules-support) (`7af7034`) | `feat/rep159-rules-support` (`7af7034`) | Stacked directly on `jrivero`'s `origin/rep159` (`0189046`..`2877687`) + `binary_rule`, `install_rule`, and `git tag -f -m` GPG fix (26/26 tests). |
| **`ros-infrastructure/ros_buildfarm`** | [`feat/rep159-binary-naming`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/rep159-binary-naming) (`a271be1` — PR 3C) | [`feat/extendable-workspace`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/extendable-workspace) (`ca13954`) | Propagates `binary_rule` to `sourcedeb`/`binarydeb`, passes `--package-prefix` to sync jobs, and isolates child release jobs (`9b02768`). |
| **`rep159-rosdistro` & `ros_buildfarm_config`** | [`feat/extendable-workspace`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/extendable-workspace) (`ab0400c` / `3322225`) | `feat/extendable-workspace` (`ab0400c` / `3322225`) | `extendable` and `extendablebin` (`extbin`) workspace release and CI configurations on `build.test.ros2.org`. |

---

## 4. Empirical Validation on `https://build.test.ros2.org` (`E*` Namespace)

| Pipeline Phase | Jenkins Job (`build.test.ros2.org`) | Build # | Status | Verified Artifact / Outcome |
|---|---|:---:|:---:|---|
| **Root `ament_package` Release** | `Esrc_uR__ament_package__ubuntu_resolute__source`<br>`Ebin_uR64__ament_package__ubuntu_resolute_amd64__binary` | `#1`<br>`#1` | **SUCCESS** | `vendor-extendable-ament-package_0.18.3-1resolute_amd64.deb` in `/opt/ros/extendable` |
| **Root `ament_cmake_core` Release** | `Esrc_uR__ament_cmake_core__ubuntu_resolute__source`<br>`Ebin_uR64__ament_cmake_core__ubuntu_resolute_amd64__binary` | `#1`<br>`#2` | **SUCCESS** | `vendor-extendable-ament-cmake-core_2.8.8-2resolute_amd64.deb` in `/opt/ros/extendable` |
| **Root `ros_workspace` Release** | `Esrc_uR__ros_workspace__ubuntu_resolute__source`<br>`Ebin_uR64__ros_workspace__ubuntu_resolute_amd64__binary` | `#1`<br>`#1` | **SUCCESS** | `vendor-extendable-ros-workspace_1.0.4-1resolute_amd64.deb` in `/opt/ros/extendable` |
| **Root APT Sync (`extendable`)** | `Erel_sync-packages-to-testing_resolute_amd64` | `#12` | **SUCCESS** | Promoted all 6 `vendor-extendable-*` packages to `http://repo.test.ros2.org/ubuntu/testing` |
| **Child `ros_workspace` Release (`extbin`)** | `Esrc_uR__extbin_ros_workspace__ubuntu_resolute__source`<br>`Ebin_uR64__extbin_ros_workspace__ubuntu_resolute_amd64__binary` | `#1`<br>`#2` | **SUCCESS** | `vendor-extendablebin-ros-workspace_1.0.4-1resolute_amd64.deb` (`ROS_WORKSPACE_PARENT_PREFIX_PATH=/opt/ros/extendable`) |
| **Child `downstream_bin_a` Release (`extbin`)** | `Esrc_uR__extbin_downstream_bin_a__ubuntu_resolute__source`<br>`Ebin_uR64__extbin_downstream_bin_a__ubuntu_resolute_amd64__binary` | `#1`<br>`#2` | **SUCCESS** | `vendor-extendablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb` generated via `bloom` |
| **Child APT Sync (`extendablebin`)** | `Erel_extbin_sync-packages-to-testing_resolute_amd64` | `#3` | **SUCCESS** | Promoted `vendor-extendablebin-*` packages to `http://repo.test.ros2.org/ubuntu/testing` |
| **Child Binary Import CI (`extendablebin`)** | `Eci__workspace-binary-import_ubuntu_resolute_amd64` | `#1` | **SUCCESS** | Installed `vendor-extendablebin-ros-workspace` & `vendor-extendable-upstream-c` from APT, sourced `/opt/ros/extendablebin/setup.sh`, built & tested `downstream_bin_a` (1/1 CTest green) |
| **Root Workspace CI (`extendable`)** | `Eci__workspace-release_ubuntu_resolute_amd64` | `#2` | **SUCCESS** | Builds and tests `ament_package`, `ament_cmake_core`, `upstream_{a,b,c}` in `extendable` (5/5 packages green) |
