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

1. **`ros-infrastructure/ros_buildfarm` — CI Workspace Dependency Walk (`feat/rep159-workspace-walk`, PR 3A)**:
   - **`scripts/ci/create_workspace.py` & `test/test_rep159_create_workspace.py` (Commits `1334bf9`, `486b579`)**: Walks source-only repositories during dependency resolution and stops workspace source checkout traversal at `binary_import` parent boundaries (leaving parent binaries to be installed via `rosdep` from APT).
   - Clean PR-ready branch cut directly off `origin/master` (zero Dockerfile pip hacks, 7/7 tests passing).

2. **`ros-infrastructure/ros_buildfarm` — Underlay & Pure-CMake Engineering Fixes (`feat/rep159-underlays`, PR 3B)**:
   - **`scripts/devel/build_and_install.py` (Commit `901c78b`)**: Added fallback to `get_default_parent_result_spaces(args.rosdistro_name)` when `--parent-result-space` is `None`, ensuring chained parent spaces are never silently dropped.
   - **`ros_buildfarm/workspace.py` (Commit `dce7ded`)**: Added dynamic export of `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, and `PATH` when underlays exist on disk without `setup.sh`.
   - **`ros_buildfarm/workspace.py` (Commit `f4d37d9`)**: Added multiarch `LD_LIBRARY_PATH` export (`lib`, `lib/x86_64-linux-gnu`, `lib/aarch64-linux-gnu`) so binaries built against pure-CMake underlay shared libraries locate `.so` targets during runtime `ctest` execution.
   - Clean PR-ready branch cut directly off `origin/master` (10/10 underlay tests + flake8 passing 100% green).

3. **`ros-infrastructure/rosdistro` (Branch: `feat/rep159-install-rule`, commit `4916cae`)**:
   - Transitive topological DAG walk & multi-parent diamond deduplication: Recursively traverses multi-tier parent hierarchies ($C \to B \to A$ and convergent diamonds) without circular dependency deadlocks or false collision errors.
   - Stacked cleanly on `feature/rep159-binary-naming-regex` (`bfde799`), 91/91 tests passing.

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
   - *Branch*: `feat/rep159-workspace-walk` (commits `1334bf9`, `486b579` off `origin/master`).
   - *Target Base*: `master`.
2. **Wave 3 (PR 3B) — `ros-infrastructure/ros_buildfarm` (Folded with Stage 2 `install_rule` Underlays)**:
   - *Title*: `feat(underlays): dynamically compute parent result spaces via install_rule and export CMake/LD paths for pure-CMake underlays`
   - *Branch*: `feat/rep159-underlays` (commits `4664f5b`..`902ccb1` off `origin/master`).
   - *Target Base*: `master`.
   - *Unblocks Release Gate 4*: **`ros_buildfarm >= 4.2.0`**.
