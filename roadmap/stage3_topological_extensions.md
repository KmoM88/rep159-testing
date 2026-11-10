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

### Decision 2: ABI Immutability Guardrails & Hybrid Override Caveat
* **Problem**: In an initial hybrid topology test (`extendablemixed`), `upstream_c` was re-declared under `binary_import` while also present in the source workspace.
* **Result**: `rosdep` and `colcon` encountered ambiguous dependency graphs, violating REP-159's core invariant that a downstream distribution cannot redefine or mutate an upstream distribution's ABI.
* **Adopted Solution**: Enforced clean distribution inheritance where downstream distributions declare only new or explicitly overridden packages, while `colcon build --ignore-src` handles the local workspace shadowing cleanly.
* **Governance Caveat (Enforcing Binary Upstream)**: Even though `rosdep --ignore-src` and local workspace overlays make it technically possible to build an upstream package from source in a chain starting with `binary_import`, **this may not be desirable production behavior**. If a downstream package links against a new source-built upstream while an intermediate `.deb` package in the underlay was linked against the original binary upstream, subtle ABI drift and One Definition Rule (ODR) violations can occur. In production distribution engineering, any `binary_import` boundary should strictly mandate binary resolution for all upstream ancestors, forcing a pure `source_rebuild` cascade whenever an ancestor package needs source patching.

### Decision 3: Multi-Parent Diamond & CI Scope for Unused Sources
* **Context**: In multi-parent convergent diamond topologies (e.g. `extendablediamond` extending `extendablebin` via `binary_import` and `extendablesrc` via `source_rebuild`), the leaf target package (`downstream_chain_a`) links exclusively against binary packages from the binary underlay branch.
* **Observation**: In the CI workspace, `downstream_src_a` from the parallel `source_rebuild` branch was checked out, compiled, and tested even though it is not part of the runtime or build-time dependency chain for `downstream_chain_a`.
* **Governance & Default Behavior Consideration**: In production distributions, running full builds and test suites on unreferenced source packages when the distribution's final leaf artifacts link against pre-installed binaries adds unnecessary CI compute cost. Future default behaviors or build policies should consider dependency-graph pruning (e.g. via `--packages-up-to` or target-based source filtering) unless explicit workspace-wide regression testing is intended.

---

## 3. Implementation Breakdown: Core Code vs. Required Fixes vs. Testing Tweaks

### Core Feature Implementation & Required Fixes (To Be Merged Upstream)

1. **`ros-infrastructure/ros_buildfarm` — CI Workspace Dependency Walk (`feat/rep159-workspace-walk` @ `486b579`, PR 3A)**:
   - **`scripts/ci/create_workspace.py` & `test/test_rep159_create_workspace.py` (Commits `1334bf9`, `486b579` by Jose Luis Rivero)**: Walks source-only repositories during dependency resolution (`ReleaseAndSourceDependencyWalker`) and stops workspace source checkout traversal at `binary_import` parent boundaries (leaving parent binaries to be installed via `rosdep` from APT).
   - Clean PR-ready branch cut directly off `origin/master` (`7daa2b1`, zero Dockerfile pip hacks, 7/7 tests passing).

2. **`ros-infrastructure/ros_buildfarm` — Underlay & Pure-CMake Engineering Fixes (`feat/rep159-underlays` @ `a4a5bbd`, PR 3B)**:
   - **Commit `83fd534` (by Jose Luis Rivero, from `9807b32`)**: `BINARY_IMPORT_DISTROS_ENV`, `get_binary_import_distros(dist_file)`, and 4 baseline unit tests in `test/test_rep159_underlay.py`.
   - **Commits `0ee8e49`, `7d23292`**: `install_rule` prefix evaluation (`get_distribution_install_prefix`) and recursive multi-tier/diamond `get_binary_import_underlays(dist_file, index)` (10/10 unit tests pass).
   - **`scripts/devel/build_and_install.py` (Commit `4c70fdc`)**: Added fallback to `get_default_parent_result_spaces(args.rosdistro_name)` when `--parent-result-space` is `None`, ensuring chained parent spaces are never silently dropped.
   - **`ros_buildfarm/workspace.py` (Commits `6b7dc03`, `a63a39d`, `a4a5bbd`)**: Added dynamic export of `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, `PATH`, and multiarch `LD_LIBRARY_PATH` (`lib`, `lib/x86_64-linux-gnu`, `lib/aarch64-linux-gnu`) when underlays exist on disk without `setup.sh`.
   - Clean PR-ready branch cut directly off `origin/master` (`7daa2b1`, 10/10 underlay tests + flake8 passing 100% green).

3. **`ros-infrastructure/rosdistro` (Branch: `feat/rep159-install-rule`, commit `a8f5543`)**:
   - Transitive topological DAG walk & multi-parent diamond deduplication: Recursively traverses multi-tier parent hierarchies ($C \to B \to A$ and convergent diamonds) without circular dependency deadlocks or false collision errors, plus Jose Luis Rivero's `BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])` (`aefe17c`, `a8f5543`).
   - Stacked cleanly on `feature/rep159-binary-naming-regex` (`bfde799`), 96/96 tests passing.

### Testing Tweaks & Local Workarounds (Test Harness Only — Do NOT Upstream)

1. **Container Tarball `pip3 install` Commits** (`fc7b990`, `aa4d978` on `rep159`; `1fd12c0`..`4f4b059` on `feat/*`):
   - Temporary pre-release overrides dropped once **Gate 1 (`rosdistro >= 1.2.0`)** and **Gate 2 (`rosdep >= 0.27.0`)** land in `ros_bootstrap` APT.
2. **Agent Docker Layer Invalidation**:
   - During local iteration of Stage 3B, Docker layer caching on `ci-agent-amd64` reused intermediate build layers that lacked the updated environment variables. A manual `docker image prune -f` and `--no-cache` run resolved the issue.
3. **Local Chained Distribution Files**:
   - `extendablechainedbin`, `extendablechainedsrc`, `extendablemixed`, and `extendablediamond` distribution specifications were created as test harness fixtures in `rep159-rosdistro`.

---

## 4. Empirical Validation & Test Evidence (`https://build.test.ros2.org`)

*(For historical local cluster builds, see [`LOCAL_BUILDFARM_SETUP.md`](../LOCAL_BUILDFARM_SETUP.md)).*

### Option A: Chained Source Rebuild ($A \xrightarrow{\text{src}} B \xrightarrow{\text{src}} C$)
* **Remote Testfarm (`build.test.ros2.org`)**: [`Eci__chained-import_ubuntu_resolute_amd64 #3`](https://build.test.ros2.org/job/Eci__chained-import_ubuntu_resolute_amd64/3/) — **SUCCESS**. Compiled all 5 repositories (`upstream_{a,b,c}`, `downstream_bin_a`, `downstream_chain_a`) from source in cascading colcon workspace and passed 5/5 CTest suites 100% green.

### Option B: Chained Binary Import ($A \xrightarrow{\text{bin}} B \xrightarrow{\text{bin}} C$)
* **Sourcedeb & Binarydeb**: [`Esrc_uR__downstream_bin_a #1`](https://build.test.ros2.org/job/Esrc_uR__downstream_bin_a__ubuntu_resolute__source/1/) and [`Ebin_uR64__downstream_bin_a #1`](https://build.test.ros2.org/job/Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary/1/) built and published `ros-extendablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb` into `building`.
* **Sync**: [`Erel_sync-packages-to-testing_resolute_amd64 #7`](https://build.test.ros2.org/job/Erel_sync-packages-to-testing_resolute_amd64/7/) (and `#10` for root `/opt/ros/extendable`) promoted the packages to `http://repo.test.ros2.org/ubuntu/testing`.
* **CI Execution**: [`Eci__chained-import_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Eci__chained-import_ubuntu_resolute_amd64/) — **SUCCESS** — Clean binary install from APT, compiled `downstream_chain_a`, linked against `libdownstream_bin_a.so` and `libupstream_c.so`, and passed all CTest suites.

### Topology 2: Hybrid Binary + Source Overriding (`--ignore-src`)
* **Remote Testfarm (`build.test.ros2.org`)**: [`Eci__mixed-chain_ubuntu_resolute_amd64 #1`](https://build.test.ros2.org/job/Eci__mixed-chain_ubuntu_resolute_amd64/1/) — **SUCCESS**. `downstream_bin_a` installed from APT binaries; `upstream_c` compiled from source in workspace, passing 2/2 test suites green.

### Topology 3: Multi-Parent Convergent Diamond DAG
* **Remote Testfarm (`build.test.ros2.org`)**: [`Eci__diamond-chain_ubuntu_resolute_amd64 #1`](https://build.test.ros2.org/job/Eci__diamond-chain_ubuntu_resolute_amd64/1/) — **SUCCESS**. Deduplicated underlays `/opt/ros/extendable:/opt/ros/extendablebin` and passed 2/2 test suites green.

---

## 5. Release-Gated Upstream PR & Release Sequence

1. **Wave 3 (PR 3A) — `ros-infrastructure/ros_buildfarm` (Blocked Until Gate 1 `rosdistro >= 1.2.0` & Gate 2 `rosdep >= 0.27.0`)**:
   - *Title*: `feat(ci): traverse source-only repos and stop workspace walk at binary_import parent boundaries`
   - *Branch*: `feat/rep159-workspace-walk` (commits `1334bf9`, `486b579` off `origin/master`).
   - *Target Base*: `master`.
2. **Wave 3 (PR 3B) — `ros-infrastructure/ros_buildfarm` (Folded with Stage 2 `install_rule` Underlays)**:
   - *Title*: `feat(underlays): dynamically compute parent result spaces via install_rule and export CMake/LD paths for pure-CMake underlays`
   - *Branch*: `feat/rep159-underlays` (commits `83fd534`..`a4a5bbd` off `origin/master`).
   - *Target Base*: `master`.
   - *Unblocks Release Gate 4*: **`ros_buildfarm >= 4.2.0`**.
