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

## 3. Implementation Breakdown: Core Code vs. Testing Tweaks

### Core Implementation (To be Merged Upstream)

1. **`ros-infrastructure/ros_buildfarm` (Branch: `feat/binary-naming-rule` / `test/stage3-binary-chained`)**:
   - **`build_and_install.py` (Commit `dd2825e`)**: Added fallback to `get_default_parent_result_spaces()` when `--parent-result-space` is passed empty, ensuring chained parent spaces are never silently dropped.
   - **`workspace.py` (Commit `12982be`)**: Added dynamic export of `CMAKE_PREFIX_PATH` and `COLCON_PREFIX_PATH` when underlays lack `setup.sh`.
   - **`workspace.py` (Commit `2a869d8`)**: Added multiarch `LD_LIBRARY_PATH` export (`lib` and `lib/<arch>`) so that binaries built against underlay shared libraries can locate them during unit testing (`ctest`).

2. **`ros/rosdistro` (Branch: `feature/rep159-install-rule`)**:
   - Transitive topological graph walk: Recursively traverses multi-tier parent hierarchies ($C \to B \to A$) without circular dependency deadlocks.

### Testing Tweaks & Local Workarounds (Test Harness Only — Do NOT Upstream)

1. **Agent Docker Layer Invalidation**:
   - During local iteration of Stage 3B, Docker layer caching on `ci-agent-amd64` reused intermediate build layers that lacked the updated environment variables. A manual `docker image prune -f` and `--no-cache` run resolved the issue.
2. **Local Chained Distribution Files**:
   - `extendablechainedbin`, `extendablechainedsrc`, and `extendablemixed` distribution specifications were created as test harness fixtures in `rep159-rosdistro`.

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

## 5. Upstream PR & Release Roadmap

1. **PR 1: `ros-infrastructure/ros_buildfarm`**
   - *Title*: `fix(underlays): ensure parent result spaces fallback and export CMake/LD paths for pure CMake underlays`
   - *Branch*: Includes commits `dd2825e`, `12982be`, and `2a869d8`.
   - *Target Base*: `master`
   - *Release Target*: `ros_buildfarm >= 4.2.0`.
