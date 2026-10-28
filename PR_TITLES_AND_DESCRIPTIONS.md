# Proposed Pull Request Titles and Descriptions for REP-159 Ecosystem

This document compiles the proposed titles, summaries, and descriptions for the upcoming Pull Requests in **`reps`** and **`rosdistro`**, focused specifically on the **Binary Package Renaming Feature**.

---

## 1. Pull Request for `openrobotics/reps`

* **Repository**: `openrobotics/reps` (or fork `KmoM88/reps`)
* **Base Branch**: `rosdistro_extension` (or `main`)
* **Head Branch**: `feature/rep-159-binary-name-templating`

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

## 2. Pull Request for `ros/rosdistro` (Binary Renaming Feature)

* **Repository**: `ros/rosdistro` (or fork `rep159-testing/rosdistro`)
* **Base Branch**: `rep159` (or `master`)
* **Head Branch**: `feature/rep159-binary-naming-regex`

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

## 3. Stacked Pull Request for `ros/rosdistro` (Custom Installation Prefixes & Dynamic Underlays)

* **Repository**: `ros/rosdistro` (or fork `rep159-testing/rosdistro`)
* **Base Branch (Stack Base)**: `feature/rep159-binary-naming-regex`
* **Head Branch**: `feature/rep159-install-rule`

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

