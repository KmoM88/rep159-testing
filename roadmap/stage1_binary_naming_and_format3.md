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

## 3. Implementation Breakdown: Core Code vs. Testing Tweaks

### Core Implementation (To be Merged Upstream)

1. **`ros/rosdistro` (Branch: `feature/rep159-binary-naming-regex`)**:
   - `DistributionFile`: Adds Format 3 parsing, `binary_rule` schema validation, and `get_binary_package_name(pkg_name)`.
   - `ReleaseRepositorySpecification`: Adds repository-level `binary_rule` support.
   - Normalization: Automatically converts underscores to hyphens and interpolates context variables (`{DISTRO}`, `{PACKAGE}`, `{ORIGIN_DISTRO}`).
   - Reverse Lookup: Implements `get_package_name_from_binary(binary_name)`.

2. **`ros-infrastructure/rosdep` (Branch: `rep159`)**:
   - `gbpdistro_support.py`: Delegates binary package queries to `dist_file.get_binary_package_name(pkg)` rather than computing `ros-%s-%s`.

3. **`ros-infrastructure/reprepro-updater` (Branch: `feat/package-prefix`)**:
   - Adds `--package-prefix` CLI option to allow selective synchronization of vendor-prefixed packages from `building` to `testing`.

4. **`ros-infrastructure/ros_buildfarm` (Branch: `feat/binary-naming-rule`)**:
   - `common.py`: Updates `get_os_package_name()` and `get_os_package_name_prefix()` to take an optional `dist_file=dist_file` argument and query `dist_file.get_binary_package_name()`.
   - Release jobs (`sourcedeb_job.py`, `binarydeb_job.py`, `create_binarydeb_task_generator.py`): Pass `dist_file=dist_file` and propagate `debian_package_name`.

### Testing Tweaks & Local Workarounds (Test Harness Only — Do NOT Upstream)

1. **Direct Tarball Pip Overrides in Dockerfiles**:
   - During local testing, `sourcepkg_task.Dockerfile.em` and `binarypkg_task.Dockerfile.em` injected pip installs of GitHub tarballs. In upstream production, `ros_buildfarm` will depend on released PyPI packages of `rosdistro` and `rosdep`.
2. **Target Repository Hostname Overrides**:
   - `release-build-local.yaml` was created to point `target_repository` to `192.168.30.202:8088`. Upstream configurations will point to standard `repo.ros2.org` endpoints.

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

## 5. Upstream PR & Release Roadmap

1. **PR 1: `openrobotics/reps`**
   - *Title*: `rep-159: document design explorations, regex decision rationale, and binary renaming in binary_import`
   - *Branch*: `feature/rep-2015-naming-and-install-rules` $\to$ `main`
2. **PR 2: `ros/rosdistro`**
   - *Title*: `feat(naming): add declarative regex-based binary package renaming engine (Format 3)`
   - *Branch*: `feature/rep159-binary-naming-regex` $\to$ `master`
   - *Release Target*: `rosdistro >= 1.0.0` on PyPI.
3. **PR 3: `ros-infrastructure/rosdep`**
   - *Title*: `feat(rep159): delegate debian package name queries to rosdistro binary_rule`
   - *Branch*: `rep159` $\to$ `master`
   - *Release Target*: `rosdep >= 0.23.0` on PyPI.
4. **PR 4: `ros-infrastructure/reprepro-updater`**
   - *Title*: `feat: add --package-prefix flag for vendor package filtering`
   - *Branch*: `feat/package-prefix` $\to$ `master`
5. **PR 5: `ros-infrastructure/ros_buildfarm`**
   - *Title*: `feat(release): delegate binary package names to rosdistro binary_rule`
   - *Branch*: `feat/binary-naming-rule` $\to$ `master`
