# Stage 1: ROSDistro Format 3 & Binary Naming Rules

## 1. Executive Summary & Problem Statement

In standard ROS 2, binary Debian and RPM package names are hardcoded to the strict pattern `ros-{distro}-{pkg_name}` (with underscores replaced by dashes).
This assumption breaks in three major operational scenarios:
1. **Vendor & Corporate Namespaces**: Organizations building proprietary or domain-specific overlays require packages under distinct prefixes (e.g., `vendor-{distro}-{pkg_name}`).
2. **Independent / Standalone Ecosystems**: Integration with software that publishes without a `ros-` prefix (e.g., Gazebo libraries publishing as `gz-sim10`).
3. **Cross-Distribution Inheritance (`binary_import`)**: When distribution `B` extends distribution `A` via `binary_import`, package managers and buildfarms must resolve the exact binary package name published by parent `A` from APT repositories.

Stage 1 establishes the **Format 3 ROSDistro specification**, introduces declarative binary package name transformation via **`binary_rule`**, and integrates resolution across `rosdistro`, `rosdep`, `reprepro-updater`, and `ros_buildfarm`.

---

## 2. Design Decisions & Technical Rationale

### Decision 1: Declarative Regex (`re.sub`) vs. Templating Engines (EmPy / Jinja2)
* **Exploration**: Prototypes were built on dedicated exploration branches using EmPy (`exploration/binary-naming-empy`) and Jinja2 (`exploration/binary-naming-jinja`).
* **Evaluation**: While templating engines provide conditionals and arbitrary Python execution, they introduce heavyweight external dependencies into minimal bootstrapping environments (`rosdistro`, `rosdep`, `bloom`, chroot build containers). Furthermore, arbitrary code execution in distribution metadata poses a security concern.
* **Adopted Solution**: A declarative search-and-replace rule powered by Python's built-in `re` module (`feature/rep159-binary-naming-regex`):
  ```yaml
  binary_rule:
    search: '^'
    replace: 'vendor-{DISTRO}-'
  ```
* **Rationale**: Zero external runtime dependencies, deterministic evaluation, immune to arbitrary code execution, and easily parsed across multiple programming languages.

### Decision 2: In-Memory Inverted Index for Reverse Mapping
* **Problem**: Build tools and dependency checkers frequently start from a binary package name (e.g., `vendor-extendable-upstream-a`) and need to determine the underlying ROS package name (`upstream_a`).
* **Adopted Solution**: `DistributionFile.get_package_name_from_binary(binary_name)` constructs an in-memory inverted mapping table when the distribution is loaded.
* **Rationale**: Eliminates costly repeated regex evaluations during large workspace walks while preserving $O(1)$ dictionary lookups.

### Decision 3: Hierarchical Precedence of Rules
* Rule evaluation follows a strict cascading hierarchy:
  1. Explicit per-package override: `binary_name` in `release/packages/<pkg>`.
  2. Repository-level override: `binary_rule` under `repositories/<repo>/release`.
  3. Distribution-level default: Top-level `binary_rule` in `distribution.yaml`.
  4. Fallback: Standard `ros-{distro}-{pkg_name}` convention.

---

## 3. Implementation Breakdown: Core Code vs. Required Fixes vs. Pre-Release Overrides

### Core Feature Implementation (To Be Merged Upstream)

1. **`ros-infrastructure/rosdistro` (Branch: `feature/rep159-binary-naming-regex` @ `3d301d6` stacked on `rep159` @ `46a7580`; Org PR [`rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1))**:
   - `DistributionFile`: Adds Format 3 parsing, `extends:` DAG resolution, `binary_rule` schema validation, and `get_binary_package_name(pkg_name)`.
   - `ReleaseRepositorySpecification`: Adds repository-level `binary_rule` support.
   - Normalization: Automatically converts underscores to hyphens and interpolates context variables (`{DISTRO}`, `{PACKAGE}`, `{ORIGIN_DISTRO}`).
   - Reverse Lookup: Implements `get_package_name_from_binary(binary_name)`.

2. **`ros-infrastructure/reprepro-updater` (Branch: `feat/package-prefix` @ `93ed2dc` off `master`/`refactor` `1e7aa5c`)**:
   - `scripts/sync_ros_packages.py` & `src/reprepro_updater/helpers.py`: Adds `-p / --package-prefix` CLI option (defaulting to `ros-<rosdistro>-`, auto-appending `-`) for `UpdateElement` naming, `FilterFormula: Package (% <prefix>*)`, `_clear_ros_distro()`, and `run_cleanup()`.
   - Zero `rosdistro` dependency; targets **`refactor`** upstream (which `ros_buildfarm` clones directly at sync job runtime).

3. **`ros-infrastructure/rosdep` (Branch: `rep159` @ `3d52dad`)**:
   - `src/rosdep2/gbpdistro_support.py` (`2d5a548`, `3d52dad`): Delegates binary package queries to `repo.release_repository.get_binary_package_name(pkg)` or `distro_file.get_binary_package_name(pkg)`, with fallback checking `extension_method == 'binary_import'`.
   - `test/test_rosdep_gbpdistro_support.py` & `test/fake_rosdistro/` (`07b6647`): Format 3 extended distribution unit tests.

4. **`ros-infrastructure/ros_buildfarm` (Branch: `feat/binary-naming-rule` @ `4062a66`)**:
   - `ros_buildfarm/common.py` (`857b025`): Updates `get_os_package_name()` and `get_os_package_name_prefix()` to accept optional `dist_file=dist_file` and query `dist_file.get_binary_package_name()`.
   - Release & sync pipeline (`argument.py`, `release_job.py`, `sourcedeb_job.py`, `sourcerpm_job.py`, `binarydeb_job.py`, `binaryrpm_job.py`, `trigger_job.py`, `append_build_timestamp.py`, `build_binarydeb.py`, `check_sync_criteria.py`, `create_binarydeb_task_generator.py`, `binarypkg_task.Dockerfile.em`, `sync_packages_to_{testing,main}_job.xml.em` in commits `61b8d29`, `ceaaef7`, `c907db2`): Propagates `dist_file`, `--debian-package-name`, and `--package-prefix`.

### Required Engineering Fixes Discovered During Validation

1. **Child Release Job Isolation in `ros_buildfarm` (`release_job.py`, commit `4062a66`)**:
   - Skips packages in `ordered_pkg_tuples` not present in `dist_file.release_packages`, preventing a `binary_import` child distribution from generating duplicate `*src_*` / `*bin_*` jobs for inherited parent packages.
2. **Renamed Package Subfolder & Assertion Lookup in `ros_buildfarm` (`binarydeb_job.py`, `binaryrpm_job.py`, `get_binarydeb.py`, commit `3397a12`)**:
   - Fixes assertion variable formatting (`debian_package_name`) and workspace subfolder / `.src.rpm` lookup when `binary_rule` renames packages away from `ros-<distro>-<pkg>`.
3. **Standalone Buildfarm Resilience Fixes (`wrapper/git.py` `ae8826b`; `jenkins.py` `199fd98`)**:
   - Retries transient TLS/GnuTLS container git errors and gracefully skips Jenkins view creation on `403 Forbidden` (Wave 0 standalone PRs).
4. **Pre-PR Cleanups Needed in `rosdep` (Post-Gate 1)**:
   - Cut a clean branch from `master`, bump `rosdistro >= 1.2.0` in `setup.py` and `python3-rosdistro-modules (>= 1.2.0)` in `stdeb.cfg`, and add a `binary_rule` test case in `test/test_rosdep_gbpdistro_support.py`.

### Temporary Pre-Release Overrides (Test Harness Only — Do NOT Upstream)

1. **`rosdep` Fork Git URL in `setup.py` & `.github/workflows/ci.yaml`** (commits `a83d852`..`b436f33`):
   - Hardcoded `rosdistro @ git+https://github.com/KmoM88/rosdistro.git@feature/rep-2015-v3-parser` and `ROSDEP_LOCAL_DEV`. Revert to standard `rosdistro >= 1.2.0` and `ros-infrastructure/ci/.github/workflows/pytest.yaml@main` once Gate 1 is published.
2. **Direct Tarball `pip3 install` & Fork URLs in `ros_buildfarm`**:
   - Tarball `pip3 install` blocks in `sourcepkg_task.Dockerfile.em`, `binarypkg_create_task.Dockerfile.em`, `binarypkg_task.Dockerfile.em`, and `release_check_sync_criteria_task.Dockerfile.em` (`1fd12c0`, `4b3072b`, `68369e9`, `efcbab3`), plus the `rep159-testing/reprepro-updater` URL in `sync_packages_to_{testing,main}_job.xml.em` (`c907db2`). Replace with `rosdistro >= 1.2.0` / `rosdep >= 0.27.0` APT dependencies and `ros-infrastructure/reprepro-updater -b refactor`.
3. **Target Repository Hostname Overrides**:
   - `release-build-local.yaml` pointing `target_repository` to `192.168.30.202:8088`.

---

## 4. Empirical Validation & Test Evidence

### Local Test Suites
* **`tools/validate_binary_naming.py` (Suite 6)**: 100% pass across all regex replacement edge cases (prefixing, suffixing, token substitution, hyphen normalization).
* **`test/test_binary_naming_rule.py`**: 6/6 unit tests passed in `ros_buildfarm`.

### Jenkins Release Pipeline Evidence

* **Local Testfarm (`192.168.30.206`)**:
  - `Usrc_uR__upstream_a__ubuntu_resolute__source` (#11): Generated `vendor-upstream-upstream-a_0.1.0-1resolute.dsc` and imported into `building`.
  - `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` (#7): Built `vendor-upstream-upstream-a_0.1.0-1resolute_amd64.deb` and ingested to reprepro.
  - `Urel_sync-packages-to-testing_resolute_amd64` (#8): Synchronized vendor package to `testing` using prefix filter `Package (% vendor-upstream-*)`.

* **Remote Testfarm (`build.test.ros2.org`)**:
  - `Usrc_uR__upstream_a` (#4): **SUCCESS** — Built sourcedeb in OSRF environment.
  - `Ubin_uR64__upstream_a` (#4): **SUCCESS** — Built binarydeb and triggered package import.
  - `Ubin_uR64__upstream_b` (#8) & `Ubin_uR64__upstream_c` (#9): **SUCCESS** — Validated multi-package dependency chain with vendor prefixing.
  - `Urel_sync-packages-to-testing_resolute_amd64` (#10): **SUCCESS** — Confirmed all vendor packages available in `building`.

---

## 5. Release-Gated Upstream PR & Release Sequence

1. **Wave 0 — `openrobotics/reps` (Spec)**:
   - *Live PR*: [`openrobotics/reps#35`](https://github.com/openrobotics/reps/pull/35) (`KmoM88:feature/rep-159-binary-name-templating` $\to$ `openrobotics:rosdistro_extension`, feeding [`openrobotics/reps#32`](https://github.com/openrobotics/reps/pull/32)).
   - *Title*: `rep-159: document design explorations, regex decision rationale, and binary renaming in binary_import`
2. **Wave 0 — `ros-infrastructure/reprepro-updater` (Zero Release Prerequisite)**:
   - *Title*: `feat: support custom --package-prefix for reprepro FilterFormula and cleanup`
   - *Branch*: `feat/package-prefix` (`93ed2dc`) $\to$ **`refactor`** *(upstream sync jobs `git clone -b refactor` directly at runtime; no PyPI/APT package step)*.
3. **Wave 0 — `ros-infrastructure/rosdistro`**:
   - *Org PR*: [`rep159-testing/rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1) (`feature/rep159-binary-naming-regex` $\to$ `rep159`); upstream target: `master`.
   - *Title*: `feat(naming): add declarative regex-based binary package renaming engine`
   - *Unblocks Release Gate 1*: Publish **`rosdistro >= 1.2.0`** (from `1.1.0`) to PyPI + OSRF `ros_bootstrap` APT (`python3-rosdistro-modules >= 1.2.0`).
4. **Wave 1 — `ros-infrastructure/rosdep` (Blocked Until Gate 1 `rosdistro >= 1.2.0`)**:
   - *Title*: `feat(rep159): delegate binary package name resolution to rosdistro binary_rule`
   - *Branch*: Clean branch off `master` cherry-picking `2d5a548`, `07b6647`, `3d52dad` (dropping `KmoM88/rosdistro` git URL hacks in `setup.py`/`ci.yaml`, bumping `rosdistro >= 1.2.0` + `stdeb.cfg`).
   - *Unblocks Release Gate 2*: Publish **`rosdep >= 0.27.0`** (from `0.26.0`) to PyPI + OSRF `ros_bootstrap` APT (`python3-rosdep-modules >= 0.27.0`).
5. **Wave 3 — `ros-infrastructure/ros_buildfarm` (Blocked Until Gate 1 + Gate 2 + `reprepro-updater:refactor`)**:
   - *Title*: `feat(release): delegate binary package names to rosdistro binary_rule and filter sync by prefix`
   - *Core + Fix Commits*: `857b025`, `61b8d29`, `ceaaef7`, `c907db2`, `3397a12`, `4062a66` $\to$ `master` (excluding `*.Dockerfile.em` tarball `pip` hacks and reverting `reprepro-updater` URL back to `ros-infrastructure/reprepro-updater -b refactor`).
   - *Unblocks Release Gate 4*: Publish **`ros_buildfarm >= 4.2.0`**.
