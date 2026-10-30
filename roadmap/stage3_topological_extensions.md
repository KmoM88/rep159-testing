# Stage 3: Multi-Tier Topological Extensions & Hybrid Overlays

## 1. Executive Summary & Problem Statement

Stages 1 and 2 validated direct parent-child relationships ($A \to B$). However, real-world robotic deployments often require multi-tier layering and hybrid development workflows:
1. **Multi-Tier Chaining ($A \to B \to C$)**: An intermediate overlay distribution (`extendablebin`) imports binaries from root (`extendable`), and a downstream leaf distribution (`extendablechainedbin`) imports binaries from `extendablebin`, requiring transitive resolution of headers, libraries, and runtime search paths.
2. **Hybrid / Mixed Workflows**: A developer workspace imports heavy dependencies as pre-built binaries from APT, while checking out a specific upstream dependency from source to apply a patch, requiring the source package to override the binary package cleanly (`--ignore-src`).

Stage 3 validates these complex topological extensions across both pure CMake packages and mixed buildsystems.

---

## 2. Design Decisions & Technical Rationale

### Decision 1: Pure CMake Packages & Environment Fallbacks
* **Context**: The test packages (`upstream_{a,b,c}`, `downstream_bin_a`, `downstream_chain_a`) were implemented as pure CMake packages (`<build_type>cmake</build_type>`) rather than `ament_cmake`.
* **Technical Issue**: Pure CMake packages installed into an underlay prefix (e.g., `/opt/ros/extendablebin`) do not automatically generate a ROS `setup.sh` shell script. As a result, standard ROS underlay sourcing fails to find downstream CMake targets.
* **Adopted Solution**: Updated `ros_buildfarm` (`workspace.py`) to detect underlays without `setup.sh` and dynamically construct and export:
  - `CMAKE_PREFIX_PATH`
  - `COLCON_PREFIX_PATH`
  - `LD_LIBRARY_PATH` (including multiarch `/lib/x86_64-linux-gnu`)
* **Rationale**: Enables buildfarms to support non-ament pure CMake repositories (Gazebo, system utilities) as first-class citizens in underlay chains.

### Decision 2: ABI Immutability Guardrails
* **Problem**: In an initial hybrid topology test (`extendablemixed`), `upstream_c` was re-declared under `binary_import` while also present in the source workspace.
* **Result**: `rosdep` and `colcon` encountered ambiguous dependency graphs, violating REP-159's core invariant that a downstream distribution cannot redefine or mutate an upstream distribution's ABI.
* **Adopted Solution**: Enforced clean distribution inheritance where downstream distributions declare only new or explicitly overridden packages, while `colcon build --ignore-src` handles the local workspace shadowing cleanly.

---

## 3. Implementation Breakdown: Core Code vs. Required Fixes vs. Testing Tweaks

### Core Feature Implementation & Required Fixes (To Be Merged Upstream)

1. **`ros-infrastructure/ros_buildfarm` — CI Workspace Dependency Walk (`origin/rep159`, PR 3A)**:
   - **`scripts/ci/create_workspace.py` & `test/test_rep159_create_workspace.py` (Commits `52b51d8`, `9736140`)**: Walks source-only repositories during dependency resolution and stops workspace source checkout traversal at `binary_import` parent boundaries (leaving parent binaries to be installed via `rosdep` from APT). *(Note: Currently lives on `origin/rep159` off `219d1a4`; must be cherry-picked alongside `feat/*` branches when opening Wave 3 PRs without rebasing active testbed branches).*

2. **`ros-infrastructure/ros_buildfarm` — Underlay & Pure-CMake Engineering Fixes (`feat/binary-naming-rule`, Folded into PR 3B)**:
   - **`scripts/ci/build_and_install.py` (Commit `dd2825e`)**: Added fallback to `get_default_parent_result_spaces(args.rosdistro_name)` when `--parent-result-space` is `None`, ensuring chained parent spaces are never silently dropped.
   - **`ros_buildfarm/workspace.py` (Commit `12982be`)**: Added dynamic export of `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, and `PATH` when underlays exist on disk without `setup.sh`.
   - **`ros_buildfarm/workspace.py` (Commit `2a869d8`)**: Added multiarch `LD_LIBRARY_PATH` export (`lib`, `lib/x86_64-linux-gnu`, `lib/aarch64-linux-gnu`) so binaries built against pure-CMake underlay shared libraries locate `.so` targets during runtime `ctest` execution.

3. **`ros-infrastructure/rosdistro` (Branch: `feature/rep159-install-rule` stacked on `rep159`)**:
   - Transitive topological DAG walk & multi-parent diamond deduplication: Recursively traverses multi-tier parent hierarchies ($C \to B \to A$ and convergent diamonds) without circular dependency deadlocks or false collision errors.

### Testing Tweaks & Local Workarounds (Test Harness Only — Do NOT Upstream)

1. **Container Tarball `pip3 install` Commits** (`fc7b990`, `aa4d978` on `rep159`; `1fd12c0`..`4f4b059` on `feat/*`):
   - Temporary pre-release overrides dropped once **Gate 1 (`rosdistro >= 1.2.0`)** and **Gate 2 (`rosdep >= 0.27.0`)** land in `ros_bootstrap` APT.
2. **Agent Docker Layer Invalidation**:
   - During local iteration of Stage 3B, Docker layer caching on `ci-agent-amd64` reused intermediate build layers that lacked the updated environment variables. A manual `docker image prune -f` and `--no-cache` run resolved the issue.
3. **Local Chained Distribution Files**:
   - `extendablechainedbin`, `extendablechainedsrc`, `extendablemixed`, and `extendablediamond` distribution specifications were created as test harness fixtures in `rep159-rosdistro`.

---

## 4. Empirical Validation & Test Evidence

### Option A: Chained Source Rebuild ($A \xrightarrow{\text{src}} B \xrightarrow{\text{src}} C$)
* **Local Testfarm**: `Eci__chained-import_ubuntu_resolute_amd64` (#3) — **SUCCESS**. Compiled all 5 repositories from source in cascading colcon workspaces. GoogleTest suites passed 100%.
* **Remote Testfarm (`build.test.ros2.org`)**: `Eci__chained-import_ubuntu_resolute_amd64` (#2) — **SUCCESS** (953s). Clean cascading source build on public OSRF runners.

### Option B: Chained Binary Import ($A \xrightarrow{\text{bin}} B \xrightarrow{\text{bin}} C$)
* **Sourcedeb & Binarydeb**: `Esrc_uR__downstream_bin_a` (#1) and `Ebin_uR64__downstream_bin_a` (#1) built and published `ros-extendablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb` into `building`.
* **Sync**: `Erel_sync-packages-to-testing_resolute_amd64` (#9 local, #7 remote) promoted the package to `testing`.
* **CI Execution**:
  - Local Build #9 to #12 diagnosed and fixed the underlay fallback, CMake prefix, and `LD_LIBRARY_PATH` bugs.
  - Local Build #13: **SUCCESS** — Clean binary install from APT, compiled `downstream_chain_a`, linked against `libdownstream_bin_a.so`, and passed all CTest and GoogleTest suites (1/1 green).

### Topology 2: Hybrid Binary + Source Overriding (`--ignore-src`)
* **Local Testfarm**: `Eci__mixed-chain_ubuntu_resolute_amd64` (#2) — **SUCCESS**. `downstream_bin_a` installed from APT binaries; `upstream_c` compiled from source in workspace, cleanly overriding the binary package.
* **Remote Testfarm (`build.test.ros2.org`)**: `Eci__mixed-chain_ubuntu_resolute_amd64` (#1) — **SUCCESS**. 2/2 test suites passed green.

---

## 5. Release-Gated Upstream PR & Release Sequence

1. **Wave 3 (PR 3A) — `ros-infrastructure/ros_buildfarm` (Blocked Until Gate 1 `rosdistro >= 1.2.0` & Gate 2 `rosdep >= 0.27.0`)**:
   - *Title*: `feat(ci): traverse source-only repos and stop workspace walk at binary_import parent boundaries`
   - *Source Commits*: `52b51d8`, `9736140` from `origin/rep159` (`scripts/ci/create_workspace.py`, `test/test_rep159_create_workspace.py`), excluding `[test only]` Dockerfile commits `fc7b990`, `aa4d978`.
   - *Target Base*: `master`.
2. **Wave 3 (PR 3B) — `ros-infrastructure/ros_buildfarm` (Folded with Stage 2 `install_rule` Underlays)**:
   - *Title*: `feat(underlays): dynamically compute parent result spaces via install_rule and export CMake/LD paths for pure-CMake underlays`
   - *Source Commits*: `006a4a1`, `80e1e0b`, `aa9f572` + Stage 3 engineering fixes `dd2825e`, `12982be`, `2a869d8` from `feat/binary-naming-rule`.
   - *Target Base*: `master`.
   - *Unblocks Release Gate 4*: **`ros_buildfarm >= 4.2.0`**.
