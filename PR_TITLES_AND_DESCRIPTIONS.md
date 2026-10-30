# Release-Gated Pull Request Titles, Descriptions & Commit Manifests for REP-159

This document compiles the complete catalog of Pull Request specifications across **`reps`**, **`rosdistro`**, **`reprepro-updater`**, **`rosdep`**, **`ros_workspace`**, **`bloom`**, and **`ros_buildfarm`**, ordered by **Release-Gated Waves** (see [roadmap/README.md](roadmap/README.md)).

For every PR beyond `rosdistro`, each entry explicitly separates:
1. **Release Gate Prerequisite** (which upstream PyPI / `ros_bootstrap` APT release must exist *before* opening/merging the PR).
2. **Core Implementation Commits** (new REP-159 functionality).
3. **Required Engineering Fixes** (integration/runtime fixes discovered during testfarm validation plus pre-PR code reconciliations).
4. **Temporary Pre-Release Overrides to Exclude** (tarball `pip` installs, fork URLs, and local node labels used only prior to upstream releases).

---

## 1. [Wave 0 — OPEN: `openrobotics/reps#35`] Pull Request for `openrobotics/reps`

* **Repository**: `openrobotics/reps` (from fork `KmoM88/reps`)
* **Base Branch**: `rosdistro_extension` (feeds [`openrobotics/reps#32`](https://github.com/openrobotics/reps/pull/32); builds on merged [`openrobotics/reps#31`](https://github.com/openrobotics/reps/pull/31))
* **Head Branch**: `feature/rep-159-binary-name-templating` (`83e4a3f`)
* **Live PR**: [`openrobotics/reps#35`](https://github.com/openrobotics/reps/pull/35) (**OPEN**)
* **Release Gate Prerequisite**: **None (Wave 0)**
* **Follow-Up Needed**: Add a formal `install_rule` schema & resolution precedence subsection to `_posts/rep-0159:2026.md` (currently referenced only briefly on line 320).

### Proposed PR Title
```text
rep-159: document design explorations, regex decision rationale, and binary renaming in binary_import
```

### Proposed PR Description
```markdown
### Summary
This PR updates the draft of **REP-159 (Distribution Extensions and Layering)** in `_posts/rep-0159:2026.md` by documenting the architectural design explorations for binary package name transformation, detailing the rationale for adopting a declarative regex search-and-replace rule (`binary_rule`), and detailing how binary renaming operates during `binary_import`.

### Background & Design Explorations
To support cross-distribution layering, standalone ecosystems (e.g., Gazebo), and vendor namespaces without recompiling from source, binary package naming must be configurable. Three design avenues were explored and prototyped:

1. **Template Engines (`empy` / `jinja2`)**:
   Evaluated dynamic template evaluation (`binary_template`) with string expressions and conditionals. While expressive, this approach introduces mandatory external third-party dependencies (`empy` or `jinja2`) into foundational, low-level bootstrapping packages (`rosdistro`, `rosdep`, `bloom`), creating unnecessary packaging friction and security/maintenance surface in minimal container and bootstrap environments.
2. **Sequential Multi-Rule Regex Pipeline (`binary_name_rules`)**:
   Evaluated an ordered list of chained regex replacement rules. While flexible, sequential rule pipelines add parsing complexity and potential chaining side-effects for standard distribution needs.
3. **Declarative Regex Search-and-Replace (`binary_rule`) — Selected Approach**:
   A single, lightweight search-and-replace rule executed using Python's built-in `re` module. It was chosen for its simplicity, deterministic behavior, and **zero additional external dependencies**, fully satisfying all identified use cases:
   * Vendor prefixes: `search: '^'`, `replace: 'vendor-{DISTRO}-'` (e.g., `vendor-extendable-upstream-a`).
   * Standalone un-prefixed packages (e.g., Gazebo): `search: '^'`, `replace: ''` (e.g., `gz-sim10`).
   * Exact package renames: `search: '^gz-cmake$'`, `replace: 'libgz-cmake5-dev'`.

### Changes Included in this PR
* **Design Explorations & Architectural Decision**: Added subsection contrasting template engines vs regex pipelines and justifying the selection of built-in regex.
* **Specification & Schema**: Formally specified `binary_rule` syntax at distribution, repository, and `extends` block levels, alongside explicit `binary_name` / `binary_names` overrides for irregular system libraries.
* **Context Variables**: Documented standard template interpolation variables (`{DISTRO}`, `{PACKAGE}`, `{ORIGIN_DISTRO}`).
* **Binary Import Behavior**: Expanded the `binary_import` section to document how declarative renaming (`binary_rule`) operates when importing pre-built binaries and resolving dependencies via `rosdep`.
* **Rationale Section**: Detailed the dependency footprint rationale and ABI preservation invariants.

### Reference Implementation
A fully functional reference implementation validating this specification across all testbed topologies has been developed and evaluated in the `rep159-testing` testbed:
* Reference `rosdistro` implementation: https://github.com/rep159-testing/rosdistro (branch `feature/rep159-binary-naming-regex`).
```

---

## 2. [Wave 0 — OPEN in Org: `rep159-testing/rosdistro#1`] Pull Request for `ros-infrastructure/rosdistro` (Binary Renaming Feature)

* **Repository**: `ros-infrastructure/rosdistro` (org fork `rep159-testing/rosdistro`)
* **Base Branch**: `rep159` (`46a7580` in org fork) / `master` (upstream, currently v`1.1.0`)
* **Head Branch**: `feature/rep159-binary-naming-regex` (`3d301d6`)
* **Live Org PR**: [`rep159-testing/rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1) (**OPEN**)
* **Release Gate Unblocked**: Together with `rep159` Format 3 base and Section 3 (`install_rule`), merging and releasing **`rosdistro >= 1.2.0`** to PyPI and OSRF `ros_bootstrap` APT (`python3-rosdistro-modules >= 1.2.0`) satisfies **Release Gate 1**.

### Proposed PR Title
```text
feat(naming): add declarative regex-based binary package renaming engine
```

### Proposed PR Description
```markdown
### Summary
Implements the declarative binary package name transformation engine (`binary_rule`) for REP-159 distribution extensions.

This feature allows extended distributions to consume and produce pre-built binary packages under custom vendor namespaces (e.g., `vendor-{DISTRO}-*`) or native upstream names (e.g., standalone Gazebo packages) without modifying upstream source manifests.

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
   * Automatically normalizes package name underscores to hyphens and interpolates `{distro}`, `{package}`, and `{origin_distro}`.
   * Supports inheritance of `binary_rule` across parent distributions and overrides within `extends` entries.
2. **Reverse Binary Alias Resolution**:
   * Added `get_package_name_from_binary(binary_name)` in `DistributionFile` constructing an in-memory inverted mapping table across active and inherited distribution trees for reverse lookups in tools like `rosdep`.
3. **Distribution Cache Integration**:
   * Updated `DistributionCache` generation to serialize and maintain `binary_rule` metadata for fast querying by downstream tools.

### Relevant Branches
* `feature/rep159-binary-naming-regex`: Core regex naming engine and test suite.
* `rep159`: Base integration branch with Format 3 distribution file support and extends DAG loader.

### Buildfarm Validation Evidence (Executed Test Jobs)
The binary renaming feature has been comprehensively tested and validated on both the local cluster and the official ROS 2 testfarm (build.test.ros2.org). All corresponding jobs completed with status SUCCESS:

* **Packaging & Release Pipeline with Vendor Renaming**:
  - Esrc_uR__upstream_a__ubuntu_resolute__source (sourcedeb generation producing vendor-extendable-upstream-a.dsc)
  - Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary (hermetic binarydeb build producing vendor-extendable-upstream-a.deb)
  - Esrc_uR__upstream_b__ubuntu_resolute__source & Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary (inter-package dependency resolution with vendor prefix)
  - Esrc_uR__upstream_c__ubuntu_resolute__source & Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary (transitive package resolution)
  - Erel_sync-packages-to-testing_resolute_amd64 (packeage promotion to testing repository using --package-prefix vendor-extendable-)
* **Downstream Binary Consumption & Resolution**:
  - Eci__nightly-release_ubuntu_resolute_amd64 (baseline distribution CI)
  - Eci__binary-import_ubuntu_resolute_amd64 (resolves renamed vendor-extendable-upstream-c debian package via rosdep, builds downstream_bin_a, and executes tests)

### Test Coverage
* Added unit test suite `test/test_binary_naming.py` validating:
  - Custom prefix rules (`custom-{distro}-{package}`)
  - Standalone empty prefix rules for Gazebo ecosystem (`gz-sim10`)
  - Exact single-package regex rules (`libgz-cmake5-dev`)
  - Distribution-level global default rules and repository-level overrides
  - Extended distribution rule inheritance and overriding in `extends`
```

---

## 3. [Wave 0 — Stacked Ready] Stacked Pull Request for `ros-infrastructure/rosdistro` (Custom Installation Prefixes & Dynamic Underlays)

* **Repository**: `ros-infrastructure/rosdistro` (org fork `rep159-testing/rosdistro`)
* **Base Branch (Stack Base)**: `feature/rep159-binary-naming-regex` (`3d301d6`)
* **Head Branch**: `feature/rep159-install-rule` (`db021b9`)
* **Release Gate Prerequisite**: **None (Wave 0 — ships inside Release Gate 1 `rosdistro >= 1.2.0`)**

### Proposed PR Title
```text
feat(rep159): support install_rule for custom installation prefixes and dynamic underlay resolution
```

### Proposed PR Description
```markdown
### Summary
> **Note**: This is a **Stacked PR** based on `feature/rep159-binary-naming-regex`. It contains only the commits implementing declarative installation prefix rules (`install_rule`) and dynamic underlay traversal across multi-tier extension DAGs.

Introduces declarative installation prefix configuration (`install_rule`) and automated ancestor underlay path resolution (`get_binary_import_underlays()`) for REP-159 distribution extensions.

### Background & Architecture
In layered, vendor, and multi-distribution architectures, binary artifacts are frequently deployed outside the standard `/opt/ros/{distro}` root (e.g., `/opt/ros/extendable`, `/opt/vendor/{distro}`, or per-package isolated prefixes).

Downstream tools (`ros_buildfarm`, `colcon`, Docker workspace generators) must programmatically determine where parent binary packages reside in order to:
1. Export `ROS_BUILDFARM_PARENT_RESULT_SPACES` across container chroots.
2. Chain multiple parent underlays without hardcoding filesystem paths.
3. Ensure CMake find modules and dynamic linkers discover pre-built libraries in layered environments.

### Features Included in this Stacked PR
1. **Declarative Install Prefix Specification (`install_rule`)**:
   * **Template String Format**: Simple template string supporting variable interpolation (e.g., `install_rule: '/opt/ros/{distro}'` or `install_rule: '/opt/vendor/{distro}'`).
   * **Regex Search-and-Replace Format**: Dictionary rule allowing fine-grained pattern rewriting:
     ```yaml
     install_rule:
       search: "^.*$"
       replace: "/opt/vendor/{distro}"
     ```
   * Defaults to canonical `/opt/ros/{distro}` if omitted.
2. **Hierarchical Scope & Inheritance**:
   * Evaluates at distribution level (`distribution.yaml: install_rule`).
   * Evaluates at release repository level (`repositories.<name>.release.install_rule`).
   * Evaluates at extension link level (`extends[].install_rule`) to override upstream prefixes.
   * Method `get_install_prefix(pkg_name)` available on `ReleaseRepositorySpecification` and `DistributionFile`.
3. **Recursive Underlay DAG Traversal (`get_binary_import_underlays`)**:
   * Added `DistributionFile.get_binary_import_underlays()` to recursively walk ancestor distribution trees.
   * Collects all active `binary_import` underlay prefixes and applies topological deduplication, preserving deterministic search order:
     `['/opt/ros/extendable', '/opt/ros/extendablebin']`
4. **Distribution Cache Integration**:
   * Serializes `install_rule` metadata into `DistributionCache` for fast HTTP query by buildfarm runners.

### Relevant Branches
* `feature/rep159-install-rule`: Head branch of this PR (contains commit `db021b9`).
* `feature/rep159-binary-naming-regex`: Base branch (Stacked on top of the binary naming PR).

### Buildfarm Validation Evidence (Executed Test Jobs)
The dynamic underlay engine has been fully validated on both the local cluster and the official ROS 2 testfarm (build.test.ros2.org) across single-tier, multi-tier chained, and diamond topologies. All corresponding jobs completed with status SUCCESS:

* **Single Underlay Validation**:
  - Eci__binary-import_ubuntu_resolute_amd64 (injects ROS_BUILDFARM_PARENT_RESULT_SPACES=/opt/ros/extendable and validates colcon build and test against binary underlay)
* **Intermediate Tier Packaging**:
  - Esrc_uR__downstream_bin_a__ubuntu_resolute__source & Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary (compiles downstream_bin_a against /opt/ros/extendable and packages it into /opt/ros/extendablebin)
* **Chained Multi-Tier Binary Underlays**:
  - Eci__chained-import_ubuntu_resolute_amd64 (injects cascading underlays /opt/ros/extendable:/opt/ros/extendablebin and links downstream_chain_a transitively across both tiers)
* **Hybrid & Diamond Convergence Topologies**:
  - Eci__mixed-chain_ubuntu_resolute_amd64 (validates dual underlays in hybrid source overlay scenarios)
  - Eci__diamond-chain_ubuntu_resolute_amd64 (validates topological deduplication when multiple DAG paths converge on shared root underlays)

### Test Coverage
* Added unit test suite `test/test_install_prefixes.py` validating:
  - Standard default ROS prefix `/opt/ros/{distro}`
  - Custom vendor template string interpolation
  - Regex search-and-replace prefix rules
  - Repository-level isolated prefix prepends
  - Distribution-level inheritance and `extends` overrides
```


---

## 4. [Wave 0 — Ready Immediately] Pull Request for `ros-infrastructure/reprepro-updater`

* **Repository**: `ros-infrastructure/reprepro-updater` (org fork `rep159-testing/reprepro-updater`)
* **Base Branch**: **`refactor`** upstream *(in `rep159-testing/reprepro-updater`, `master` @ `1e7aa5c` tracks upstream `refactor`, where `scripts/sync_ros_packages.py` resides)*
* **Head Branch**: `feat/package-prefix` (`93ed2dc`)
* **Release Gate Prerequisite**: **None (Wave 0)** — Zero dependency on `rosdistro` or `rosdep`. Furthermore, `reprepro-updater` has no PyPI/APT release cycle: `ros_buildfarm` sync jobs `git clone -b refactor` directly at runtime.
* **Core Implementation Commits**: `93ed2dc` (`scripts/sync_ros_packages.py`, `src/reprepro_updater/helpers.py`)
* **Temporary Overrides to Exclude**: None.

### Proposed PR Title
```text
feat: support custom --package-prefix for reprepro FilterFormula and cleanup
```

### Proposed PR Description
```markdown
### Summary
Adds an optional `-p / --package-prefix` CLI flag to `scripts/sync_ros_packages.py` (defaulting to `ros-<rosdistro>-` for 100% backward compatibility) and threads `package_prefix` through `UpdateElement` creation, `FilterFormula`, `_clear_ros_distro()`, and `run_cleanup()`.

### Motivation (REP-159)
Under REP-159 (`binary_rule`), extended or vendor ROS distributions may publish Debian packages using custom prefixes (e.g., `vendor-extendable-*`) rather than `ros-<rosdistro>-*`. Parameterizing the package prefix allows `sync_ros_packages.py` to synchronize and clean up custom-prefixed packages between `building`, `testing`, and `main` suites without altering default ROS behavior.

### Notes on Target Branch
Targets `refactor`, matching the branch cloned by `ros_buildfarm` `sync_packages_to_{testing,main}_job.xml.em`.
```

---

## 5. [Wave 0 — Ready Immediately] Standalone Resilience & Tooling Bugfix PRs (`ros_buildfarm` & `bloom`)

These three bugfixes were uncovered during REP-159 buildfarm and packaging validation, have **zero dependency on `rosdistro` Format 3**, and can be opened against upstream `master` immediately in **Wave 0**:

### 5A. `ros-infrastructure/ros_buildfarm` — Transient TLS/Network Git Retry
* **Target Base**: `master`
* **Cherry-Pick Commit**: `ae8826b` (`scripts/wrapper/git.py` from `feat/binary-naming-rule`)
* **Release Gate Prerequisite**: **None (Wave 0)**
* **Proposed PR Title**:
  ```text
  fix(git): retry transient GnuTLS/curl connection errors in git wrapper
  ```
* **Summary**: Extends `scripts/wrapper/git.py` retry error matching with `GnuTLS recv error`, `TLS connection was non-properly terminated`, `Connection reset by peer`, and `RPC failed; curl` to prevent spurious container clone failures under heavy CI load.

### 5B. `ros-infrastructure/ros_buildfarm` — Graceful Fallback on Restricted Jenkins View Permissions
* **Target Base**: `master`
* **Cherry-Pick Commits**: `2823cf1`, `199fd98`, `40231f3` (`ros_buildfarm/jenkins.py` portion only, excluding Dockerfile pip lines in `40231f3`)
* **Release Gate Prerequisite**: **None (Wave 0)**
* **Proposed PR Title**:
  ```text
  fix(jenkins): warn and skip view creation/reconfiguration on HTTP 403 Forbidden
  ```
* **Summary**: Allows non-admin testfarm users with job-configuration permissions (but without global Jenkins view-creation permissions) to run `generate_*_jobs.py` cleanly instead of aborting on `403 Forbidden`.

### 5C. `ros-infrastructure/bloom` — GPG-Signed Git Tag Compatibility
* **Target Base**: `master`
* **Cherry-Pick Commit**: `d6fdf9e` (`bloom/generators/debian/generator.py` from `feat/rep159-rules-support`)
* **Release Gate Prerequisite**: **None (Wave 0)**
* **Proposed PR Title**:
  ```text
  fix(debian): supply tag message (-m) in git tag -f to support tag.gpgSign=true
  ```
* **Summary**: Updates `bloom/generators/debian/generator.py` (line 869) to invoke `'git tag -f -m "' + tag_name + '" ' + tag_name`, preventing `fatal: no tag message?` aborts on developer machines configured with `tag.gpgSign=true`.

---

## 6. [Wave 1 — Gated on `rosdistro >= 1.2.0`] Pull Request for `ros-infrastructure/rosdep`

* **Repository**: `ros-infrastructure/rosdep` (org fork `rep159-testing/rosdep`, currently v`0.26.0`)
* **Base Branch**: `master`
* **Source Branch**: `rep159` (`3d52dad`) — *cut a clean feature branch directly from `master`*
* **Release Gate Prerequisite**: **BLOCKED until Release Gate 1 (`rosdistro >= 1.2.0` published on PyPI and OSRF `ros_bootstrap` APT)**.
* **Core Implementation Commits**:
  - `2d5a548` & `3d52dad`: `src/rosdep2/gbpdistro_support.py` delegating binary package name resolution to `repo.release_repository.get_binary_package_name(pkg)` / `distro_file.get_binary_package_name(pkg)` with `extension_method == 'binary_import'` fallback.
  - `07b6647`: `test/test_rosdep_gbpdistro_support.py` and `test/fake_rosdistro/{index-v4.yaml, base/, derived_binary/, derived_source/}`.
* **Required Pre-PR Fixes**:
  1. Bump `'rosdistro >= 1.2.0'` in `setup.py` and `python3-rosdistro-modules (>= 1.2.0)` in `stdeb.cfg`.
  2. Add unit test assertions in `test/test_rosdep_gbpdistro_support.py` exercising custom `binary_rule` (`vendor-{distro}-` and empty prefix) via `get_binary_package_name()`.
* **Temporary Pre-Release Overrides to Exclude**:
  - Drop commits `a83d852`, `366891f`, `e88ba75`, `2b41634`, `b436f33` (which hardcoded `rosdistro @ git+https://github.com/KmoM88/rosdistro.git@feature/rep-2015-v3-parser` and `ROSDEP_LOCAL_DEV` in `setup.py` and replaced `ros-infrastructure/ci/.github/workflows/pytest.yaml@main` in `.github/workflows/ci.yaml`).
* **Release Gate Unblocked**: Publishing **`rosdep >= 0.27.0`** to PyPI and `ros_bootstrap` APT satisfies **Release Gate 2**.

### Proposed PR Title
```text
feat(rep159): delegate OS binary package name resolution to rosdistro binary_rule
```

### Proposed PR Description
```markdown
### Summary
Updates `rosdep2.gbpdistro_support.get_gbprepo_as_rosdep_data()` to resolve OS binary package names via `rosdistro`'s `get_binary_package_name(pkg)` API (introduced in `rosdistro >= 1.2.0` for REP-159 Format 3 distributions) instead of unconditionally formatting `'ros-%s-%s' % (release_name, pkg)`.

### Changes Included
1. **Binary Name Delegation (`src/rosdep2/gbpdistro_support.py`)**:
   * Queries `repo.release_repository.get_binary_package_name(pkg)` or `distro_file.get_binary_package_name(pkg)`.
   * Preserves full backward compatibility for Format 2 distributions and older mock objects.
2. **Dependency Version Pinning (`setup.py`, `stdeb.cfg`)**:
   * Requires `rosdistro >= 1.2.0` / `python3-rosdistro-modules (>= 1.2.0)`.
3. **Unit Tests (`test/test_rosdep_gbpdistro_support.py`, `test/fake_rosdistro/`)**:
   * Tests Format 3 `binary_import` vs. `source_rebuild` inheritance and `binary_rule` prefix transformations.
```

---

## 7. [Wave 1 — Branch Reconciliation Needed] Pull Request for `ros2/ros_workspace`

* **Repository**: `ros2/ros_workspace` (org fork `rep159-testing/ros_workspace`, currently v`1.0.3` on `main`)
* **Base Branch**: `main`
* **Source Branches to Reconcile**: `rep159-parent-chain` (`12f93e9`) + `feat/composable-underlay-chaining` (`032d161`)
* **Release Gate Prerequisite**: **Wave 1** (independent CMake PR; building a child distro's `ros_workspace` `.deb` via Bloom requires Gate 3).
* **Required Pre-PR Engineering Reconciliation**:
  1. Keep `12f93e9`'s multi-prefix search loop (`${CMAKE_INSTALL_PREFIX};${ROS_WORKSPACE_PARENT_PREFIX_PATH}`) for locating `ament_package` templates/egg-links when a `binary_import` child distribution inherits `ament_package` from a parent underlay rather than re-releasing it.
  2. Keep `12f93e9`'s hermetic default (`SKIP_PARENT_PREFIX_PATH="SKIP_PARENT_PREFIX_PATH"`) when neither `ROS_WORKSPACE_PARENT_PREFIX_PATH` nor `PARENT_PREFIX_PATH` is passed at configure time, so standalone root ROS 2 distributions remain unchanged.
  3. Accept both `ROS_WORKSPACE_PARENT_PREFIX_PATH` (passed by `bloom`) and `PARENT_PREFIX_PATH` (`032d161`), normalize `;` to `:`, and register the `parent_prefix_path` ament index resource.
* **Release Gate Unblocked**: Tagging and releasing **`ros_workspace >= 1.0.4`** satisfies **Release Gate 2B**.

### Proposed PR Title
```text
feat(rep159): support parent underlay chaining and parent ament_package discovery
```

---

## 8. [Wave 2 — Gated on `rosdistro >= 1.2.0` + `rosdep >= 0.27.0`] Pull Request for `ros-infrastructure/bloom`

* **Repository**: `ros-infrastructure/bloom` (org fork `rep159-testing/bloom`, currently v`0.14.4`)
* **Base Branch**: `rep159` (`2877687` in org fork) / `master` (upstream)
* **Source Branches**: `rep159` (`0189046`, `29a329c`, `db66bf6`, `2877687`) + `feat/rep159-rules-support` (`1f62809`, `d6fdf9e`)
* **Release Gate Prerequisite**: **BLOCKED until Release Gate 1 (`rosdistro >= 1.2.0`) AND Release Gate 2 (`rosdep >= 0.27.0`) are published on PyPI & APT** (plus `ros_workspace >= 1.0.4` for `-DROS_WORKSPACE_PARENT_PREFIX_PATH` runtime contract).
* **Core Implementation Commits**:
  - `0189046`..`2877687` (`rep159`): `get_binary_import_parents()` and `get_ros_workspace_dependencies()` in `bloom/rosdistro_api.py`; `ParentPrefixes` underlay sourcing loops, `CMAKE_PREFIX_PATH`/`PKG_CONFIG_PATH` chaining, and `-DROS_WORKSPACE_PARENT_PREFIX_PATH` injection in `bloom/generators/debian/templates/{ament_cmake,cmake}/rules.em`.
  - `1f62809` (`feat/rep159-rules-support`): `get_binary_package_name()` and `get_install_prefix()` in `bloom/rosdistro_api.py`; `InstallationPrefix` and `rosify_package_name()` delegation in `bloom/generators/rosdebian.py`; unit & golden template tests (`test_rosdistro_api.py`, `test_rosdebian.py`, `test_rules_templates.py`, `test_generator.py`).
* **Required Engineering Fixes**:
  1. **Committed (`d6fdf9e`)**: `git tag -f -m` fix in `bloom/generators/debian/generator.py` (if not already merged via Wave 0 PR 5C).
  2. **Pre-PR Code Fix Required (`bloom/rosdistro_api.py:get_install_prefix()`)**: Replace `dist_file.install_rule.replace('{distro}', distro)` (lines 269–270, which fails on regex `dict` `install_rule` and silently falls back to `/opt/ros/<distro>`) with direct delegation to `dist_file.get_install_prefix(pkg_name)`.
  3. **Pre-PR Dependency Pins**: Bump `rosdistro >= 1.2.0` and `rosdep >= 0.27.0` in `setup.py` and `python3-rosdistro (>= 1.2.0)`, `python3-rosdep (>= 0.27.0)` in `stdeb.cfg`.
  4. **Scope Note**: Document that Debian packaging (`rosdebian.py`) is covered in this PR, with RPM (`rosrpm.py`) tracked as a follow-up.
* **Release Gate Unblocked**: Publishing **`bloom >= 0.15.0`** satisfies **Release Gate 3**.

### Proposed PR Title
```text
feat(debian): support REP-159 binary_rule, install_rule, and parent underlay chaining
```

---

## 9. [Wave 3 — Gated on Gates 1 & 2 + `reprepro-updater:refactor`] Modular Pull Requests for `ros-infrastructure/ros_buildfarm`

* **Repository**: `ros-infrastructure/ros_buildfarm` (org fork `rep159-testing/ros_buildfarm`, currently v`4.1.1+master`)
* **Base Branch**: `master`
* **Release Gate Prerequisite**: **BLOCKED until**:
  1. **Release Gate 1 (`rosdistro >= 1.2.0`)** is published to PyPI **and** OSRF `ros_bootstrap` APT (`python3-rosdistro-modules >= 1.2.0` across `focal..resolute`),
  2. **Release Gate 2 (`rosdep >= 0.27.0`)** is published to PyPI **and** OSRF `ros_bootstrap` APT (`python3-rosdep >= 0.27.0`),
  3. **Wave 0 PR 4 (`reprepro-updater --package-prefix`)** is merged into `ros-infrastructure/reprepro-updater:refactor`.
* **Non-Destructive Branch Preparation Rule**:
  - Do **not** rebase active testbed branches (`rep159`, `feat/install-prefixes`, `feat/binary-naming-rule`, `feat/cache-job-rep159`). Instead, cherry-pick the clean core + engineering-fix commits from `origin/rep159` and `origin/feat/binary-naming-rule` onto three focused PR branches off upstream `master`, **omitting all 6 `*.Dockerfile.em` tarball `pip3 install` overrides, the fork `reprepro-updater` URL, and the `rosdistro_cache_job.xml.em` `assignedNode` override**.

---

### 9A. `ros_buildfarm` PR 3A — CI Workspace Dependency Walk Across Extended Distributions
* **Core Commits (from `origin/rep159`)**: `52b51d8`, `9736140` (`scripts/ci/create_workspace.py`, `test/test_rep159_create_workspace.py`)
* **Temporary Commits Excluded**: `fc7b990`, `aa4d978` (`[test only]` Dockerfile pip overrides)
* **Proposed PR Title**:
  ```text
  feat(ci): resolve source-only repos and stop workspace walk at binary_import parents
  ```
* **Summary**: Updates `scripts/ci/create_workspace.py` to traverse source-only repositories during dependency calculation while halting source checkout recursion at `binary_import` parent distribution boundaries so inherited parent packages are installed from APT via `rosdep`.

---

### 9B. `ros_buildfarm` PR 3B — Dynamic Install Prefixes, Recursive Ancestor Underlays & Pure-CMake Runtime Support
* **Core Commits (from `feat/install-prefixes` / `feat/binary-naming-rule`)**:
  - `006a4a1`, `80e1e0b`, `aa9f572` (`ros_buildfarm/common.py`, `ros_buildfarm/ci_job.py`, `scripts/ci/build_and_test.py`, `test/test_rep159_underlay.py`)
* **Required Engineering Fixes Folded into PR 3B**:
  - `dd2825e` (`scripts/ci/build_and_install.py`): Fall back to `get_default_parent_result_spaces(args.rosdistro_name)` when `--parent-result-space` is `None`.
  - `12982be` & `2a869d8` (`ros_buildfarm/workspace.py`): Export `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, `PATH`, and multiarch `LD_LIBRARY_PATH` (`lib`, `lib/x86_64-linux-gnu`, `lib/aarch64-linux-gnu`) when an underlay prefix exists on disk without `setup.sh` (supporting pure-CMake underlays during both compilation and `ctest` runtime).
* **Temporary Commits Excluded**: `40231f3` (Dockerfile pip lines), `4f4b059` (`create_workspace.Dockerfile.em` tarball install).
* **Proposed PR Title**:
  ```text
  feat(underlays): resolve parent result spaces via install_rule and export CMake/LD fallbacks
  ```

---

### 9C. `ros_buildfarm` PR 3C — Binary Naming Rule Delegation, Child Release Isolation & Prefix-Filtered Sync
* **Core Commits (from `feat/binary-naming-rule`)**:
  - `857b025`, `61b8d29`, `ceaaef7`, `c907db2` *(with `reprepro-updater` URL kept as `ros-infrastructure/reprepro-updater` `-b refactor`)* across `ros_buildfarm/{common.py, argument.py, release_job.py, sourcedeb_job.py, sourcerpm_job.py, binarydeb_job.py, binaryrpm_job.py, trigger_job.py}`, `scripts/release/{append_build_timestamp.py, build_binarydeb.py, check_sync_criteria.py, create_binarydeb_task_generator.py}`, `templates/release/deb/{binarypkg_task.Dockerfile.em, sync_packages_to_testing_job.xml.em, sync_packages_to_main_job.xml.em}`, and `test/test_binary_naming_rule.py`.
  - Bump `'rosdistro >= 1.2.0'` in `setup.py` and `python3-rosdistro-modules (>= 1.2.0)` in `stdeb.cfg` (ensuring `rosdistro_cache_task.Dockerfile.em` and `release_check_sync_criteria_task.Dockerfile.em` also pull Format 3 `rosdistro` from `ros_bootstrap` APT automatically).
* **Required Engineering Fixes Folded into PR 3C**:
  - `4062a66` (`ros_buildfarm/release_job.py`): Skip packages in `ordered_pkg_tuples` not present in `dist_file.release_packages`, preventing child `binary_import` distributions from generating duplicate release jobs for inherited parent packages.
  - `3397a12` (`ros_buildfarm/binarydeb_job.py`, `ros_buildfarm/binaryrpm_job.py`, `scripts/release/get_binarydeb.py`): Fix assertion variable formatting (`debian_package_name`) and fallback workspace directory / `.src.rpm` glob lookup when `binary_rule` renames packages.
* **Temporary Commits Excluded**: `1fd12c0`, `4b3072b`, `68369e9`, `efcbab3` (Dockerfile tarball `pip3 install` overrides), fork `rep159-testing/reprepro-updater` URL in `c907db2`, and `8c1f978`/`6f62d7b` (`rosdistro_cache_job.xml.em` `assignedNode` override).
* **Proposed PR Title**:
  ```text
  feat(release): delegate OS package naming to rosdistro binary_rule and isolate child release jobs
  ```
