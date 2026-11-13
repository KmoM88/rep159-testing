# Release-Gated Pull Request Titles, Descriptions & Commit Manifests for REP-159

This document compiles the complete catalog of Pull Request specifications across **`reps`**, **`rosdistro`**, **`rosdistro-reviewer`**, **`reprepro-updater`**, **`rosdep`**, **`ros_workspace`**, **`ros_workspace_shell`**, **`bloom`**, **`ros_buildfarm`**, and **`ros_gz`**, ordered by **Release-Gated Waves** (see [`ROLLOUT_PLAN.md`](ROLLOUT_PLAN.md) and [`roadmap/README.md`](roadmap/README.md)).

For every PR beyond `rosdistro`, each entry explicitly separates:
1. **Release Gate Prerequisite** (which upstream PyPI / `ros_bootstrap` APT release must exist *before* opening/merging the PR).
2. **Core Implementation Commits** (including adopted commits by Jose Luis Rivero `<jrivero@honurobotics.com>`).
3. **Required Engineering Fixes** (integration/runtime fixes discovered during testfarm validation).
4. **Temporary Pre-Release Overrides Excluded** (tarball `pip` installs, fork URLs, and local node labels left behind on testbed branches).

---

## 1. [Wave 0 — MERGED: `openrobotics/reps#35` & Ready: `1aef980`, `0905caa`] Pull Requests for `openrobotics/reps`

* **Repository**: `openrobotics/reps` (from fork `KmoM88/reps`)
* **Base Branch**: `rosdistro_extension` (feeds [`openrobotics/reps#32`](https://github.com/openrobotics/reps/pull/32); builds on merged [`openrobotics/reps#31`](https://github.com/openrobotics/reps/pull/31))
* **Merged Spec PR**: [`openrobotics/reps#35`](https://github.com/openrobotics/reps/pull/35) (**MERGED** as `f683ccc` on `openrobotics:rosdistro_extension` — standardizing strictly on lowercase `{distro}`, `{package}`, `{origin_distro}`)
* **Stacked Spec Branches Ready to Open**:
  1. `KmoM88:feature/rep-159-install-rule` (`1aef980`, rebased cleanly on `f683ccc`)
  2. `KmoM88:feature/rep-159-workspace-package` (`0905caa`, stacked on `1aef980`)
* **Release Gate Prerequisite**: **None (Wave 0)**

### 1A. Merged PR Title (`openrobotics/reps#35` @ `f683ccc`)
```text
rep-159: document design explorations, regex decision rationale, and binary renaming in binary_import
```

### 1B. Ready-to-Open Stacked Spec PR (`KmoM88:feature/rep-159-install-rule` @ `1aef980`)
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

### 1C. Ready-to-Open Stacked Spec PR (`KmoM88:feature/rep-159-workspace-package` @ `0905caa`)
* **Proposed PR Title**:
  ```text
  rep-159: specify configurable workspace_package (ros_workspace_shell) and Index v4 distribution_eol_date
  ```
* **Proposed PR Description**:
  ```markdown
  ### Summary
  Extends `_posts/rep-0159:2026.md` with:
  1. **Configurable `workspace_package` (`ros_workspace` vs. `ros_workspace_shell`)**:
     - Allows Format 3 `distribution.yaml` files to declare `workspace_package: ros_workspace_shell` (defaulting to `ros_workspace`) so non-ROS / plain-CMake distributions (such as Gazebo Jetty) can provide `/opt/ros/<distro>/{setup.sh,local_setup.sh}` without requiring `ament_package` or `ament_cmake_core`.
     - Generalizes `BINARY_IMPORT_OVERRIDABLE` so `binary_import` child distributions override and release their configured `workspace_package`.
  2. **Index v4 `distribution_eol_date`**:
     - Specifies optional `distribution_eol_date: YYYY-MM-DD` metadata on distribution entries in `index-v4.yaml`.
  ```

---

## 2. [Wave 0 — OPEN in Org: `rep159-testing/rosdistro#1`] Pull Request for `ros-infrastructure/rosdistro` (Binary Renaming Feature)

* **Repository**: `ros-infrastructure/rosdistro` (org fork `rep159-testing/rosdistro`)
* **Base Branch**: `rep159` (`46a7580` in org fork, including Jose Luis Rivero's Format 3 parser & parent cache loading) / `master` (upstream, currently v`1.1.0`)
* **Head Branch**: `feature/rep159-binary-naming-regex` (`bfde799`)
* **Live Org PR**: [`rep159-testing/rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1) (**OPEN**)
* **Release Gate Unblocked**: Together with `rep159` Format 3 base and Section 3 (`feat/rep159-install-rule`, `feat/rep159-eol-date`, `feat/rep159-workspace-package`), merging and releasing **`rosdistro >= 1.2.0`** to PyPI and OSRF `ros_bootstrap` APT (`python3-rosdistro-modules >= 1.2.0`) satisfies **Release Gate 1**.

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
```

---

## 3. [Wave 0 — Stacked Ready] Stacked Pull Requests for `ros-infrastructure/rosdistro` (`install_rule`, `distribution_eol_date`, and `workspace_package`)

* **Repository**: `ros-infrastructure/rosdistro` (org fork `rep159-testing/rosdistro`)
* **Stack Lineage**:
  1. `feat/rep159-install-rule` (`a8f5543`, based on `feature/rep159-binary-naming-regex` `bfde799` — **96/96 unit tests pass**)
  2. `feat/rep159-eol-date` (`5ec62f9`, stacked on `a8f5543` — **100/100 unit tests pass**)
  3. `feat/rep159-workspace-package` (`3670bd8`, stacked on `5ec62f9` — **106/106 unit tests pass**)
* **Release Gate Prerequisite**: **None (Wave 0 — ships inside Release Gate 1 `rosdistro >= 1.2.0`)**

### Commits Included Across the Stack (`a8f5543` $\to$ `5ec62f9` $\to$ `3670bd8`)
- `db021b9` & `4916cae`: Declarative `install_rule` prefix evaluation (canonical lowercase `{distro}`, `{package}`, `{origin_distro}`) and recursive `get_binary_import_underlays()`.
- `aefe17c` & `a8f5543` (**Jose Luis Rivero**, cherry-picked from `origin/rep159-child-ros-workspace` `4a89ac4` & `78c7db8`): Enforces `BINARY_IMPORT_OVERRIDABLE = frozenset(['ros_workspace'])`.
- `5ec62f9` (`feat/rep159-eol-date`): Parses optional `distribution_eol_date` (`YYYY-MM-DD`) in `rosdistro/index.py` (Index v4).
- `5d4a392` (**Jose Luis Rivero**, cherry-picked from `origin/rep159-shell` `bc0600f`): Adds `workspace_package` field (`get_workspace_package()`, defaulting to `'ros_workspace'`) and generalizes `BINARY_IMPORT_OVERRIDABLE` to `{self.get_workspace_package()}`.
- `3670bd8` (`feat/rep159-workspace-package`): Fixes `get_binary_package_name()` lookup in `rosdistro/distribution_file.py` for hyphenated ROS/Gazebo package names (`gz-cmake`, `gz-math`, `gz-tools2`, `gz-msgs`, `gz-transport`).

### Proposed PR Titles
- **PR 3A (`feat/rep159-install-rule` @ `a8f5543`)**:
  ```text
  feat(rep159): support install_rule prefixes, recursive underlays, and child ros_workspace override
  ```
- **PR 3B (`feat/rep159-eol-date` @ `5ec62f9`)**:
  ```text
  feat(index): parse optional distribution_eol_date in index v4
  ```
- **PR 3C (`feat/rep159-workspace-package` @ `3670bd8`)**:
  ```text
  feat(rep159): support configurable workspace_package and hyphenated package binary lookup
  ```

---

## 4. [Wave 0 — Ready Immediately] Pull Request for `ros-infrastructure/rosdistro-reviewer` (`distribution_eol_date`)

* **Repository**: `ros-infrastructure/rosdistro-reviewer` (org fork `rep159-testing/rosdistro-reviewer`)
* **Base Branch**: `main` (`6287250`)
* **Head Branch**: `feat/rep159-eol-date` (`3e6ab56`)
* **Release Gate Prerequisite**: **None (Wave 0)** — Zero dependency on `rosdistro >= 1.2.0` (**200/200 unit & linter tests pass**).
* **Core Implementation Commit**: `3e6ab56` (`rosdistro_reviewer/index_yaml_check.py`, `test/rosdistro_reviewer/test_index_yaml_check.py`).

### Proposed PR Title
```text
feat(index): validate optional distribution_eol_date (YYYY-MM-DD) in index-v4.yaml
```

---

## 5. [Wave 0 — Ready Immediately] Pull Request for `ros-infrastructure/reprepro-updater`

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

## 6. [Wave 0 — Ready Immediately] Standalone Resilience & Tooling Bugfix PRs (`ros_buildfarm` & `bloom`)

These three bugfixes have **zero dependency on `rosdistro` Format 3** and can be opened against upstream `master` immediately in **Wave 0**:

1. **`ros-infrastructure/ros_buildfarm` — Transient TLS/Network Git Retry (`ae8826b` in `scripts/wrapper/git.py`)**:
   - Title: `fix(git): retry transient GnuTLS/curl connection errors in git wrapper`
2. **`ros-infrastructure/ros_buildfarm` — Graceful Fallback on Restricted Jenkins View Permissions (`2823cf1`, `199fd98` in `ros_buildfarm/jenkins.py`)**:
   - Title: `fix(jenkins): warn and skip view creation/reconfiguration on HTTP 403 Forbidden`
3. **`ros-infrastructure/bloom` — GPG-Signed Git Tag Compatibility (`d6fdf9e` in `bloom/generators/debian/generator.py`)**:
   - Title: `fix(debian): supply tag message (-m) in git tag -f to support tag.gpgSign=true`

---

## 7. [Wave 1 — Gated on `rosdistro >= 1.2.0`] Pull Request for `ros-infrastructure/rosdep`

* **Repository**: `ros-infrastructure/rosdep` (org fork `rep159-testing/rosdep`, currently v`0.26.0`)
* **Base Branch**: `master`
* **Clean PR-Ready Branch**: `feat/rep159-binary-lookup` (`5661779`, cut directly off `origin/master` `c2eb4b0`; org PR [`rosdep#2`](https://github.com/rep159-testing/rosdep/pull/2))
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

## 8. [Wave 1 — Clean PR Ready on `jrivero`'s Base] Pull Requests for `ros2/ros_workspace` & `ros_workspace_shell`

### 8A. `ros2/ros_workspace` (`feat/rep159-parent-chaining` @ `4997f85`)
* **Base Branch**: `main` (`db49f0a`)
* **Clean PR-Ready Branch**: `feat/rep159-parent-chaining` (`4997f85`), directly based on Jose Luis Rivero's `origin/rep159-parent-chain` (`12f93e9`).
* **Commits Included**:
  1. `12f93e9` (**Jose Luis Rivero**): Multi-prefix search loop (`${CMAKE_INSTALL_PREFIX};${ROS_WORKSPACE_PARENT_PREFIX_PATH}`) for locating `ament_package` templates when inherited from a parent underlay, hermetic `SKIP_PARENT_PREFIX_PATH` default for root distros, and `parent_prefix_path` ament resource index registration.
  2. `4997f85`: 5-line CMake variable alias accepting `PARENT_PREFIX_PATH` when `ROS_WORKSPACE_PARENT_PREFIX_PATH` is unset.
* **Proposed PR Title**:
  ```text
  feat(rep159): support parent underlay chaining and parent ament_package discovery
  ```

### 8B. `ros_workspace_shell` (`feat/rep159-unset-current-prefix` @ `b6a8195`)
* **Base Branch**: `main` (`a89cc7b`, tagged `0.1.0` by Jose Luis Rivero)
* **Clean PR-Ready Branch**: `feat/rep159-unset-current-prefix` (`b6a8195`)
* **Commit Included**:
  - `b6a8195` (`templates/setup.sh.in`): Unsets `AMENT_CURRENT_PREFIX` after sourcing each parent prefix so parent Ament distributions (such as `lyrical`) do not leak `AMENT_CURRENT_PREFIX` into plain-CMake or child prefixes.
* **Proposed PR Title**:
  ```text
  fix(setup): unset AMENT_CURRENT_PREFIX after sourcing parent prefixes
  ```

---

## 9. [Wave 2 — Gated on `rosdistro >= 1.2.0` + `rosdep >= 0.27.0`] Pull Requests for `ros-infrastructure/bloom`

* **Repository**: `ros-infrastructure/bloom` (org fork `rep159-testing/bloom`, currently v`0.14.4`)
* **Base Branch**: `master` (`98be0c5`)
* **Clean PR-Ready Stack**:
  1. `feat/rep159-rules-support` (`7af7034`, stacked on Jose Luis Rivero's `origin/rep159` `0189046`..`2877687` — **26/26 unit tests pass**)
  2. `feat/rep159-workspace-package` (`ec0bcca`, stacked on `7af7034` — **37/37 unit tests pass**)
* **Release Gate Prerequisite**: **BLOCKED until Release Gate 1 (`rosdistro >= 1.2.0`) AND Release Gate 2 (`rosdep >= 0.27.0`) are published on PyPI & APT**.
* **Commits Included**:
  - `0189046`..`2877687` (**Jose Luis Rivero**, `origin/rep159`): `get_binary_import_parents()` and `get_ros_workspace_dependencies()` in `bloom/rosdistro_api.py`; `ParentPrefixes` underlay sourcing loops, `CMAKE_PREFIX_PATH`/`PKG_CONFIG_PATH` chaining, and `-DROS_WORKSPACE_PARENT_PREFIX_PATH` injection in `bloom/generators/debian/templates/{ament_cmake,cmake}/rules.em`.
  - `1f62809`..`7af7034` (`feat/rep159-rules-support`): `get_binary_package_name()` and `get_install_prefix()` (including `dist_file.get_install_prefix()` delegation in `45fb575`), `InstallationPrefix` and `rosify_package_name()` delegation in `bloom/generators/rosdebian.py`, and `git tag -f -m` GPG fix (`d6fdf9e`).
  - `aa5133e` (**Jose Luis Rivero**, cherry-picked from `origin/rep159-shell` `2cb93dc`): Adds `get_workspace_package(distro)` and generalizes `get_ros_workspace_dependencies()` and `rules.em` for `ros_workspace_shell` / `ros_workspace`.
  - `ebfa37a`: Uses `rosdistro.get_distribution_file()` in `bloom/rosdistro_api.py` so `extends` and `workspace_package` metadata are preserved when generating Debian tracks for extended distributions without a pre-built child cache.
  - `ec0bcca`: Adds `unset AMENT_CURRENT_PREFIX;` after sourcing each parent `setup.sh` in `bloom/generators/debian/templates/{ament_cmake,cmake}/rules.em`.
* **Release Gate Unblocked**: Publishing **`bloom >= 0.15.0`** satisfies **Release Gate 3**.

### Proposed PR Title
```text
feat(debian): support REP-159 binary_rule, install_rule, workspace_package, and parent underlay chaining
```

---

## 10. [Wave 3 — Gated on Gates 1 & 2 + `reprepro-updater:refactor`] Modular Pull Requests for `ros-infrastructure/ros_buildfarm`

* **Repository**: `ros-infrastructure/ros_buildfarm` (org fork `rep159-testing/ros_buildfarm`, currently v`4.1.1+master`)
* **Base Branch**: `master` (`7daa2b1`)
* **Clean PR-Ready Branches**: Four focused PR branches cut off `origin/master` (`7daa2b1`) with **zero Dockerfile tarball `pip` hacks** (all temporary tarball overrides remain isolated on testbed branches `feat/binary-naming-rule` @ `797d771`, `feat/extendable-workspace` @ `ca13954`, and `feat/extendable-workspace-package` @ `b242685`).

### 10A. `ros_buildfarm` PR 3A — CI Workspace Dependency Walk (`feat/rep159-workspace-walk` @ `486b579`)
* **Commits (by Jose Luis Rivero, cherry-picked from `origin/rep159` `52b51d8` & `9736140`)**:
  - `1334bf9` & `486b579` (`scripts/ci/create_workspace.py`, `test/test_rep159_create_workspace.py`): `ReleaseAndSourceDependencyWalker` traversing source-only repositories during dependency calculation while halting source checkout recursion at `binary_import` parent boundaries (**7/7 unit tests pass**).
* **Proposed PR Title**:
  ```text
  feat(ci): resolve source-only repos and stop workspace walk at binary_import parents
  ```

### 10B. `ros_buildfarm` PR 3B — Dynamic Install Prefixes, Recursive Underlays & Multi-Parent Isolation (`feat/rep159-underlays` @ `274640b`)
* **Commits (stacked on Jose Luis Rivero's `9807b32` commit)**:
  - `83fd534` (**Jose Luis Rivero**, from `9807b32` on `origin/rep159`): `BINARY_IMPORT_DISTROS_ENV`, `get_binary_import_distros(dist_file)`, and 4 baseline unit tests in `test/test_rep159_underlay.py`.
  - `0ee8e49` & `7d23292`: `get_distribution_install_prefix()`, recursive multi-tier/diamond `get_binary_import_underlays(dist_file, index)` honoring `install_rule`, and 6 additional unit tests.
  - `4c70fdc` (`scripts/devel/build_and_install.py`): Fall back to `get_default_parent_result_spaces(args.rosdistro_name)` when `--parent-result-space` is `None`.
  - `6b7dc03`, `a63a39d`, `a4a5bbd` (`ros_buildfarm/workspace.py`): Export `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, `PATH`, and multiarch `LD_LIBRARY_PATH` when an underlay prefix exists on disk without `setup.sh`.
  - `a9a60e2` & `274640b` (`ros_buildfarm/workspace.py`, `test/test_rep159_underlay.py`): Export `CMAKE_PREFIX_PATH` for `parent_result_spaces` with `setup.sh` (`ros_workspace_shell`) and unset `AMENT_CURRENT_PREFIX` after sourcing each parent `setup.sh` in `call_build_tool()` (**11/11 unit tests pass**).
* **Proposed PR Title**:
  ```text
  feat(underlays): resolve parent result spaces via install_rule and isolate multi-parent CMake/Ament env
  ```

### 10C. `ros_buildfarm` PR 3C — Binary Naming Rule Delegation, Child Release Isolation & Prefix-Filtered Sync (`feat/rep159-binary-naming` @ `a271be1`)
* **Commits**:
  - `a1f57c6`..`a271be1`: Delegates `get_os_package_name()` and `get_os_package_name_prefix()` to `dist_file.get_binary_package_name()` / `binary_rule` (strictly lowercase `{distro}`), propagates `--debian-package-name` and `--package-prefix`, fixes renamed subfolder assertion lookups (`79cc19a`), and isolates child `binary_import` release jobs in `release_job.py` (`9b02768`) (**6/6 unit tests pass**).
* **Proposed PR Title**:
  ```text
  feat(release): delegate OS package naming to rosdistro binary_rule and isolate child release jobs
  ```

### 10D. `ros_buildfarm` PR 3D — Configurable `workspace_package` Release Job Filtering (`feat/rep159-workspace-package` @ `e54594c`, stacked on `a271be1`)
* **Commit (by Jose Luis Rivero, cherry-picked from `origin/rep159-shell` `146d05f`)**:
  - `e54594c` (`ros_buildfarm/release_job.py`): Queries `dist_file.get_workspace_package()` when filtering inherited `binary_import` packages so custom workspace packages (`ros_workspace_shell`) are properly recognized alongside `ros_workspace`.
* **Proposed PR Title**:
  ```text
  feat(release): support configurable workspace_package in release job generation
  ```

---

## 11. [Wave 4 — Vendorless ROS 2 + Gazebo Bridge] Pull Request for `gazebosim/ros_gz`

* **Repository**: `gazebosim/ros_gz` (org fork `rep159-testing/ros_gz`)
* **Base Branch**: `ros2` (tag `3.0.12` @ `04a4544`)
* **Clean PR-Ready Branch**: `feat/rep159-vendorless-bridge` (`08645e3`, modifying **only 3 files** `+17/-22` lines with all sibling subdirectories intact)
* **Testbed Branch**: `feat/rep159-no-vendor` (`efec554`, which additionally pruned sibling `ros_gz_*` subdirectories so `create_workspace.py` in CI only built `ros_gz_interfaces` and `ros_gz_bridge`)
* **Core Implementation Commit (`08645e3`)**:
  - `ros_gz_interfaces/package.xml`: Replaces `<depend>gz_cmake_vendor</depend>` and `<depend>gz_msgs_vendor</depend>` with `<depend>gz-cmake</depend>` and `<depend>gz-msgs</depend>`.
  - `ros_gz_bridge/package.xml` & `ros_gz_bridge/CMakeLists.txt`: Replaces `<depend>gz_cmake_vendor</depend>`, `<depend>gz_math_vendor</depend>`, `<depend>gz_msgs_vendor</depend>`, and `<depend>gz_transport_vendor</depend>` with direct `gz-cmake`, `gz-math`, `gz-msgs`, and `gz-transport` dependencies and direct unversioned `find_package(gz-math / gz-msgs / gz-transport REQUIRED)`.

### Proposed PR Title
```text
feat(rep159): build ros_gz_interfaces and ros_gz_bridge directly against Gazebo packages without vendor wrappers
```
