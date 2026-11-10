# Release-Gated Pull Request Titles, Descriptions & Commit Manifests for REP-159

This document compiles the complete catalog of Pull Request specifications across **`reps`**, **`rosdistro`**, **`reprepro-updater`**, **`rosdep`**, **`ros_workspace`**, **`bloom`**, and **`ros_buildfarm`**, ordered by **Release-Gated Waves** (see [`ROLLOUT_PLAN.md`](ROLLOUT_PLAN.md) and [`roadmap/README.md`](roadmap/README.md)).

For every PR beyond `rosdistro`, each entry explicitly separates:
1. **Release Gate Prerequisite** (which upstream PyPI / `ros_bootstrap` APT release must exist *before* opening/merging the PR).
2. **Core Implementation Commits** (including adopted commits by Jose Luis Rivero `<jrivero@honurobotics.com>`).
3. **Required Engineering Fixes** (integration/runtime fixes discovered during testfarm validation).
4. **Temporary Pre-Release Overrides Excluded** (tarball `pip` installs, fork URLs, and local node labels left behind on testbed branches).

---

## 1. [Wave 0 — MERGED: `openrobotics/reps#35` & Ready: `feature/rep-159-install-rule`] Pull Requests for `openrobotics/reps`

* **Repository**: `openrobotics/reps` (from fork `KmoM88/reps`)
* **Base Branch**: `rosdistro_extension` (feeds [`openrobotics/reps#32`](https://github.com/openrobotics/reps/pull/32); builds on merged [`openrobotics/reps#31`](https://github.com/openrobotics/reps/pull/31))
* **Merged Spec PR**: [`openrobotics/reps#35`](https://github.com/openrobotics/reps/pull/35) (**MERGED** as `f683ccc` on `openrobotics:rosdistro_extension` — standardizing strictly on lowercase `{distro}`, `{package}`, `{origin_distro}`)
* **Stacked Spec Branch Ready to Open**: `KmoM88:feature/rep-159-install-rule` (`f0118d5`, rebased cleanly on `f683ccc`)
* **Release Gate Prerequisite**: **None (Wave 0)**

### 1A. Merged PR Title (`openrobotics/reps#35` @ `f683ccc`)
```text
rep-159: document design explorations, regex decision rationale, and binary renaming in binary_import
```

### 1B. Ready-to-Open Stacked Spec PR (`KmoM88:feature/rep-159-install-rule` @ `f0118d5`)
* **Proposed PR Title**:
  ```text
  rep-159: add formal specification for custom installation prefixes (install_rule)
  ```
* **Proposed PR Description**:
  ```markdown
  ### Summary
  Adds the formal specification for declarative installation prefix rules (`install_rule`) to `_posts/rep-0159:2026.md` on `rosdistro_extension` (building on #35):
  - Supports simple string templates (`install_rule: "/opt/vendor/{distro}"`) and regex `search`/`replace` dictionaries (`{distro}`, `{package}`, `{origin_distro}`).
  - Specifies hierarchical precedence (`extends[].install_rule` -> repository `release.install_rule` -> distribution `install_rule` -> default `/opt/ros/{distro}`).
  - Documents recursive `binary_import` underlay chaining (`get_binary_import_underlays()`) and `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
  ```

---

## 2. [Wave 0 — OPEN in Org: `rep159-testing/rosdistro#1`] Pull Request for `ros-infrastructure/rosdistro` (Binary Renaming Feature)

* **Repository**: `ros-infrastructure/rosdistro` (org fork `rep159-testing/rosdistro`)
* **Base Branch**: `rep159` (`46a7580` in org fork, including Jose Luis Rivero's Format 3 parser & parent cache loading) / `master` (upstream, currently v`1.1.0`)
* **Head Branch**: `feature/rep159-binary-naming-regex` (`bfde799`)
* **Live Org PR**: [`rep159-testing/rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1) (**OPEN**)
* **Release Gate Unblocked**: Together with `rep159` Format 3 base and Section 3 (`feat/rep159-install-rule`), merging and releasing **`rosdistro >= 1.2.0`** to PyPI and OSRF `ros_bootstrap` APT (`python3-rosdistro-modules >= 1.2.0`) satisfies **Release Gate 1**.

### Proposed PR Title
```text
feat(naming): add declarative regex-based binary package renaming engine
```

### Proposed PR Description
```markdown
### Summary
Implements the declarative binary package name transformation engine (`binary_rule`) for REP-159 distribution extensions.

This feature allows extended distributions to consume and produce pre-built binary packages under custom vendor namespaces (e.g., `vendor-{distro}-*`) or native upstream names (e.g., standalone Gazebo packages) without modifying upstream source manifests.

### Evaluated Exploration Branches & Selected Design
During the prototyping phase, three distinct naming engines were evaluated on dedicated exploration branches:
* `exploration/binary-naming-empy`: Implemented dynamic template evaluation via EmPy.
* `exploration/binary-naming-jinja`: Implemented sandboxed template evaluation via Jinja2.
* `exploration/binary-naming-regex`: Evaluated sequential regex replacement rules.

**Decision**: The single search-and-replace regex engine (`feature/rep159-binary-naming-regex`) was selected because it relies exclusively on Python's built-in `re` module, adding **zero external library dependencies** to `rosdistro` while fully covering vendor prefixing, un-prefixed native libraries, and regex token replacement.

### Features & Fixes Included
1. **Declarative Binary Naming (`binary_rule`)**:
   * Added `get_binary_package_name(pkg_name)` to `ReleaseRepositorySpecification` and `DistributionFile`.
   * Evaluates `search` and `replace` using Python's standard `re.sub()`.
   * Automatically normalizes package name underscores to hyphens and interpolates canonical lowercase `{distro}`, `{package}`, and `{origin_distro}`.
   * Supports inheritance of `binary_rule` across parent distributions and overrides within `extends` entries.
2. **Reverse Binary Alias Resolution**:
   * Added `get_package_name_from_binary(binary_name)` in `DistributionFile` constructing an in-memory inverted mapping table across active and inherited distribution trees for reverse lookups in tools like `rosdep`.
3. **Distribution Cache Integration**:
   * Updated `DistributionCache` generation to serialize and maintain `binary_rule` metadata for fast querying by downstream tools.

### Buildfarm Validation Evidence (build.test.ros2.org)
* **Packaging & Release Pipeline with Vendor Renaming (`extendable`)**:
  - `Esrc_uR__upstream_a__ubuntu_resolute__source` #2, `Esrc_uR__upstream_b` #1, `Esrc_uR__upstream_c` #1 (SUCCESS)
  - `Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary` #1, `Ebin_uR64__upstream_b` #1, `Ebin_uR64__upstream_c` #1 (SUCCESS)
  - `Erel_sync-packages-to-testing_resolute_amd64` #8 (SUCCESS — `--package-prefix vendor-extendable-`)
* **Downstream Binary Consumption & Resolution**:
  - `Eci__nightly-release_ubuntu_resolute_amd64` #2, `Eci__source-branches` #2, `Eci__release-branches` #2 (SUCCESS)
  - `Eci__binary-import_ubuntu_resolute_amd64` #5 (SUCCESS — resolves `vendor-extendable-upstream-c` via `rosdep`)
```

---

## 3. [Wave 0 — Stacked Ready] Stacked Pull Request for `ros-infrastructure/rosdistro` (`install_rule` + Child `ros_workspace` Override)

* **Repository**: `ros-infrastructure/rosdistro` (org fork `rep159-testing/rosdistro`)
* **Base Branch (Stack Base)**: `feature/rep159-binary-naming-regex` (`bfde799`)
* **Head Branch**: `feat/rep159-install-rule` / `feature/rep159-install-rule` (`a8f5543`)
* **Release Gate Prerequisite**: **None (Wave 0 — ships inside Release Gate 1 `rosdistro >= 1.2.0`)**

### Commits Included in `feat/rep159-install-rule` (`a8f5543`)
- `db021b9` & `4916cae`: Declarative `install_rule` prefix evaluation (canonical lowercase `{distro}`, `{package}`, `{origin_distro}`) and recursive `get_binary_import_underlays()`.
- `aefe17c` & `a8f5543` (**Jose Luis Rivero**, cherry-picked from `origin/rep159-child-ros-workspace` `4a89ac4` & `78c7db8`): Enforces `BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])` so a `binary_import` child distribution is allowed and required to release its own `ros_workspace` package while keeping all other parent packages immutable.

### Proposed PR Title
```text
feat(rep159): support install_rule prefixes, recursive underlays, and child ros_workspace override
```

### Proposed PR Description
```markdown
### Summary
> **Note**: This is a **Stacked PR** based on `feature/rep159-binary-naming-regex` (#1).

Introduces declarative installation prefix configuration (`install_rule`), automated ancestor underlay path resolution (`get_binary_import_underlays()`), and child `ros_workspace` release override enforcement (`BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])`) for REP-159 distribution extensions.

### Features Included in this Stacked PR
1. **Declarative Install Prefix Specification (`install_rule`)**:
   * **Template String Format**: Supports lowercase variable interpolation (`install_rule: '/opt/ros/{distro}'` or `install_rule: '/opt/vendor/{distro}'`).
   * **Regex Search-and-Replace Format**: Dictionary rule allowing fine-grained pattern rewriting (`search` / `replace`).
   * Evaluates at `extends[]`, repository `release`, and distribution levels, defaulting to `/opt/ros/{distro}`.
2. **Recursive Underlay DAG Traversal (`get_binary_import_underlays`)**:
   * Recursively walks ancestor distribution trees, collecting active `binary_import` underlay prefixes in topological order with diamond deduplication.
3. **Child `ros_workspace` Release Enforcement (`aefe17c`, `a8f5543` by Jose Luis Rivero)**:
   * Defines `BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])` so a `binary_import` child distribution can and must release its own `ros_workspace` package (establishing `/opt/ros/<child>/setup.sh` chained to parent underlays) while keeping all other inherited parent packages immutable.

### Test Coverage
* All 96 unit tests in `test/` pass (`test_install_prefixes.py`, `test_binary_naming.py`, `test_rep159.py`).
```

---

## 4. [Wave 0 — Ready Immediately] Pull Request for `ros-infrastructure/reprepro-updater`

* **Repository**: `ros-infrastructure/reprepro-updater` (org fork `rep159-testing/reprepro-updater`)
* **Base Branch**: **`refactor`** upstream *(in `rep159-testing/reprepro-updater`, `master` @ `1e7aa5c` tracks upstream `refactor`, where `scripts/sync_ros_packages.py` resides)*
* **Head Branch**: `feat/package-prefix` (`93ed2dc`)
* **Release Gate Prerequisite**: **None (Wave 0)** — Zero dependency on `rosdistro` or `rosdep`. `ros_buildfarm` sync jobs `git clone -b refactor` directly at runtime.
* **Core Implementation Commits**: `93ed2dc` (`scripts/sync_ros_packages.py`, `src/reprepro_updater/helpers.py`)

### Proposed PR Title
```text
feat: support custom --package-prefix for reprepro FilterFormula and cleanup
```

---

## 5. [Wave 0 — Ready Immediately] Standalone Resilience & Tooling Bugfix PRs (`ros_buildfarm` & `bloom`)

These three bugfixes have **zero dependency on `rosdistro` Format 3** and can be opened against upstream `master` immediately in **Wave 0**:

1. **`ros-infrastructure/ros_buildfarm` — Transient TLS/Network Git Retry (`ae8826b` in `scripts/wrapper/git.py`)**:
   - Title: `fix(git): retry transient GnuTLS/curl connection errors in git wrapper`
2. **`ros-infrastructure/ros_buildfarm` — Graceful Fallback on Restricted Jenkins View Permissions (`2823cf1`, `199fd98` in `ros_buildfarm/jenkins.py`)**:
   - Title: `fix(jenkins): warn and skip view creation/reconfiguration on HTTP 403 Forbidden`
3. **`ros-infrastructure/bloom` — GPG-Signed Git Tag Compatibility (`d6fdf9e` in `bloom/generators/debian/generator.py`)**:
   - Title: `fix(debian): supply tag message (-m) in git tag -f to support tag.gpgSign=true`

---

## 6. [Wave 1 — Gated on `rosdistro >= 1.2.0`] Pull Request for `ros-infrastructure/rosdep`

* **Repository**: `ros-infrastructure/rosdep` (org fork `rep159-testing/rosdep`, currently v`0.26.0`)
* **Base Branch**: `master`
* **Clean PR-Ready Branch**: `feat/rep159-binary-lookup` (`5661779`, cut directly off `origin/master` `c2eb4b0`)
* **Release Gate Prerequisite**: **BLOCKED until Release Gate 1 (`rosdistro >= 1.2.0` published on PyPI and OSRF `ros_bootstrap` APT)**.
* **Core Implementation Commit**:
  - `5661779` (distilled from `2d5a548`, `3d52dad`, `07b6647` on `rep159`): `src/rosdep2/gbpdistro_support.py` delegating binary package name resolution to `repo.release_repository.get_binary_package_name(pkg)` / `distro_file.get_binary_package_name(pkg)` with `extension_method == 'binary_import'` fallback, plus `test/test_rosdep_gbpdistro_support.py` and `test/fake_rosdistro/` fixtures (including `derived_naming`).
* **Temporary Pre-Release Overrides Excluded**:
  - Zero CI or `setup.py` git URL hacks (`a83d852`..`b436f33` remain exclusively on testbed branch `rep159`).

### Proposed PR Title
```text
feat(rep159): delegate OS binary package name resolution to rosdistro binary_rule
```

---

## 7. [Wave 1 — Clean PR Ready on `jrivero`'s Base] Pull Request for `ros2/ros_workspace`

* **Repository**: `ros2/ros_workspace` (org fork `rep159-testing/ros_workspace`, currently v`1.0.3` on `main`)
* **Base Branch**: `main` (`db49f0a`)
* **Clean PR-Ready Branch**: `feat/rep159-parent-chaining` (`4997f85`), directly based on Jose Luis Rivero's `origin/rep159-parent-chain` (`12f93e9`).
* **Commits Included**:
  1. `12f93e9` (**Jose Luis Rivero**): Multi-prefix search loop (`${CMAKE_INSTALL_PREFIX};${ROS_WORKSPACE_PARENT_PREFIX_PATH}`) for locating `ament_package` templates when inherited from a parent underlay, hermetic `SKIP_PARENT_PREFIX_PATH` default for root distros, and `parent_prefix_path` ament resource index registration.
  2. `4997f85`: 5-line CMake variable alias accepting `PARENT_PREFIX_PATH` when `ROS_WORKSPACE_PARENT_PREFIX_PATH` is unset.
* **Release Gate Unblocked**: Tagging and releasing **`ros_workspace >= 1.0.4`** satisfies **Release Gate 2B**.

### Proposed PR Title
```text
feat(rep159): support parent underlay chaining and parent ament_package discovery
```

---

## 8. [Wave 2 — Gated on `rosdistro >= 1.2.0` + `rosdep >= 0.27.0`] Pull Request for `ros-infrastructure/bloom`

* **Repository**: `ros-infrastructure/bloom` (org fork `rep159-testing/bloom`, currently v`0.14.4`)
* **Base Branch**: `master` (`98be0c5`)
* **Clean PR-Ready Branch**: `feat/rep159-rules-support` (`7af7034`), stacked directly on Jose Luis Rivero's `origin/rep159` (`0189046`..`2877687`).
* **Release Gate Prerequisite**: **BLOCKED until Release Gate 1 (`rosdistro >= 1.2.0`) AND Release Gate 2 (`rosdep >= 0.27.0`) are published on PyPI & APT**.
* **Commits Included**:
  - `0189046`..`2877687` (**Jose Luis Rivero**, `origin/rep159`): `get_binary_import_parents()` and `get_ros_workspace_dependencies()` in `bloom/rosdistro_api.py`; `ParentPrefixes` underlay sourcing loops, `CMAKE_PREFIX_PATH`/`PKG_CONFIG_PATH` chaining, and `-DROS_WORKSPACE_PARENT_PREFIX_PATH` injection in `bloom/generators/debian/templates/{ament_cmake,cmake}/rules.em`.
  - `1f62809` (`feat/rep159-rules-support`): `get_binary_package_name()` and `get_install_prefix()` in `bloom/rosdistro_api.py`; `InstallationPrefix` and `rosify_package_name()` delegation in `bloom/generators/rosdebian.py`; unit & golden template tests.
  - `d6fdf9e`: `git tag -f -m` fix in `bloom/generators/debian/generator.py`.
  - `45fb575`: Direct delegation to `dist_file.get_install_prefix()` for regex `dict` `install_rule` support.
  - `7af7034`: Canonical lowercase `{distro}`, `{package}`, `{origin_distro}` across all test fixtures (26/26 unit tests pass).
* **Release Gate Unblocked**: Publishing **`bloom >= 0.15.0`** satisfies **Release Gate 3**.

### Proposed PR Title
```text
feat(debian): support REP-159 binary_rule, install_rule, and parent underlay chaining
```

---

## 9. [Wave 3 — Gated on Gates 1 & 2 + `reprepro-updater:refactor`] Modular Pull Requests for `ros-infrastructure/ros_buildfarm`

* **Repository**: `ros-infrastructure/ros_buildfarm` (org fork `rep159-testing/ros_buildfarm`, currently v`4.1.1+master`)
* **Base Branch**: `master` (`7daa2b1`)
* **Clean PR-Ready Branches**: Three focused, non-overlapping PR branches cut directly off `origin/master` (`7daa2b1`) with **zero Dockerfile tarball `pip` hacks** (all temporary tarball overrides remain isolated on testbed branch `feat/binary-naming-rule` @ `797d771`).

### 9A. `ros_buildfarm` PR 3A — CI Workspace Dependency Walk (`feat/rep159-workspace-walk` @ `486b579`)
* **Commits (by Jose Luis Rivero, cherry-picked from `origin/rep159` `52b51d8` & `9736140`)**:
  - `1334bf9` & `486b579` (`scripts/ci/create_workspace.py`, `test/test_rep159_create_workspace.py`): `ReleaseAndSourceDependencyWalker` traversing source-only repositories during dependency calculation while halting source checkout recursion at `binary_import` parent boundaries (7/7 unit tests pass).
* **Proposed PR Title**:
  ```text
  feat(ci): resolve source-only repos and stop workspace walk at binary_import parents
  ```

### 9B. `ros_buildfarm` PR 3B — Dynamic Install Prefixes, Recursive Underlays & Pure-CMake Runtime Support (`feat/rep159-underlays` @ `a4a5bbd`)
* **Commits (stacked on Jose Luis Rivero's `9807b32` commit)**:
  - `83fd534` (**Jose Luis Rivero**, from `9807b32` on `origin/rep159`): `BINARY_IMPORT_DISTROS_ENV`, `get_binary_import_distros(dist_file)`, and 4 baseline unit tests in `test/test_rep159_underlay.py`.
  - `0ee8e49` & `7d23292`: `get_distribution_install_prefix()`, recursive multi-tier/diamond `get_binary_import_underlays(dist_file, index)` honoring `install_rule`, and 6 additional unit tests (10/10 pass).
  - `4c70fdc` (`scripts/devel/build_and_install.py`): Fall back to `get_default_parent_result_spaces(args.rosdistro_name)` when `--parent-result-space` is `None`.
  - `6b7dc03`, `a63a39d`, `a4a5bbd` (`ros_buildfarm/workspace.py`): Export `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, `PATH`, and multiarch `LD_LIBRARY_PATH` when an underlay prefix exists on disk without `setup.sh` (supporting pure-CMake underlays during compilation and `ctest` runtime).
* **Proposed PR Title**:
  ```text
  feat(underlays): resolve parent result spaces via install_rule and export CMake/LD fallbacks
  ```

### 9C. `ros_buildfarm` PR 3C — Binary Naming Rule Delegation, Child Release Isolation & Prefix-Filtered Sync (`feat/rep159-binary-naming` @ `a271be1`)
* **Commits**:
  - `a1f57c6`..`a271be1`: Delegates `get_os_package_name()` and `get_os_package_name_prefix()` to `dist_file.get_binary_package_name()` / `binary_rule` (strictly lowercase `{distro}`), propagates `--debian-package-name` and `--package-prefix`, fixes renamed subfolder assertion lookups, and isolates child `binary_import` release jobs in `release_job.py` (`9b02768`) (6/6 unit tests pass).
* **Proposed PR Title**:
  ```text
  feat(release): delegate OS package naming to rosdistro binary_rule and isolate child release jobs
  ```
