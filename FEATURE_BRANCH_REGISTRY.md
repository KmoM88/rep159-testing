# REP-159 Feature & Branch Registry

This document registers the chronological sequence of **Features**, the associated **Git Branches** across all submodules, their base branches, validation statuses, and upstream integration/rebase strategies for [REP 159](https://github.com/openrobotics/reps/pull/32).

---

## 1. Branching Model & Release-Gated Upstream Strategy

To maintain maximum traceability, testbed stability, and clean upstream Pull Request creation:

1. **Testbed Feature Branches (`feat/<name>`, `feature/<name>`)**:
   - Developed inside [`rep159-testing`](https://github.com/rep159-testing) forks (and [`KmoM88/reps`](https://github.com/KmoM88/reps) targeting [`openrobotics/reps:rosdistro_extension`](https://github.com/openrobotics/reps/pull/32)).
   - Where downstream tools (`rosdep`, `ros_buildfarm`) depend on unreleased `rosdistro` / `rosdep` features, active branches temporarily carry **pre-release bootstrap overrides** (e.g., `pip3 install ...tar.gz` in `*.Dockerfile.em` or fork git URLs) so Jenkins CI and release pipelines can run end-to-end before upstream PyPI / `ros_bootstrap` APT releases exist.
2. **Integration & Collaborator Branches (`rep159`, `test/rep159-<name>`, `rep159-*`)**:
   - Shared integration baselines (`origin/rep159` across `rosdistro`, `rosdep`, `ros_buildfarm`, `bloom`, `ros_buildfarm_config`, plus `ros_workspace:rep159-parent-chain` and `rosdistro:rep159-child-ros-workspace`).
3. **Strict Non-Destructive Progression ("Never rebase or overwrite active testbed branches")**:
   - Active tracking and validated testbed branches (`master`, `main`, `rep159`, and `ros_buildfarm` `feat/*`) are **never rebased or force-overwritten**.
   - Once upstream **Release Gates** publish package $X$ with feature $Y$ to PyPI and `ros_bootstrap` APT, dedicated clean upstream PR branches are cut by cherry-picking **(A) Core Feature Commits** + **(B) Required Engineering Fixes** while excluding **(C) Temporary Pre-Release Overrides** (see [roadmap/README.md](roadmap/README.md)).

---

## 2. Feature Tracking Matrix

```
[FEAT-0: Baseline MVP] ──► [FEAT-1: binary_rule] ──► [FEAT-2: install_rule] ──► [FEAT-3: buildfarm naming & sync] ──► [FEAT-4: reps spec] ──► [FEAT-5: release pipeline & APT repo] ──► [FEAT-6: multi-tier topologies] ──► [FEAT-7: composable suite & ros_workspace] ──► [FEAT-8: cache lifecycle] ──► [FEAT-9: bloom packaging]
   (rosdistro format 3)       (regex renaming engine)      (prefix resolution)          (common.py + reprepro-updater)       (openrobotics/reps)     (reprepro/docker & release jobs)         (extendable family A->B->C)              (bloom fork / ros_workspace deb / C*)    (rosdistro_build_cache)      (git-bloom-generate rosdebian)
```

| ID | Feature / Component | Repository | Development Branch (`@ SHA`) | Actual Base Branch | Release Gate / Live PR | Local Test Status | Jenkins CI Status |
|---|---|---|---|---|---|:---:|:---:|
| **FEAT-0** | Baseline REP-159 MVP (Walk, ABI guardrails, Format 3) | `rosdistro`<br>`rosdep`<br>`ros_buildfarm`<br>`ros_buildfarm_config` | `rep159` (`46a7580`)<br>`rep159` (`3d52dad`)<br>`rep159` (`9736140`)<br>`rep159` | `master`<br>`master`<br>`master` (`219d1a4`)<br>`master` | Wave 0 (`rosdistro`)<br>Gate 1 $\to$ `rosdep`<br>Gates 1+2 $\to$ `ros_buildfarm` | ✅ 100% (Suites 1-5) | ✅ **SUCCESS** (5/5 jobs) |
| **FEAT-1** | Regex Binary Renaming Engine (`binary_rule`) | `rosdistro`<br>`rosdep` | `feature/rep159-binary-naming-regex` (`3d301d6`)<br>`rep159` (`3d52dad`) | `rep159` (`46a7580`)<br>`master` | [`rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1) (**OPEN**)<br>Gated on `rosdistro >= 1.2.0` | ✅ 100% (Suite 6) | ✅ **SUCCESS** (Validated with debs) |
| **FEAT-2** | Dynamic Installation Prefixes & Underlays (`install_rule`) | `rosdistro`<br>`ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-rosdistro` | `feature/rep159-install-rule` (`db021b9`)<br>**`feat/install-prefixes`** (`4f4b059`)<br>`feat/install-rule`<br>`feat/install-rule` | `feature/rep159-binary-naming-regex`<br>**`master`** (`7daa2b1`)<br>`rep159`<br>`feat/binary-naming-rule` | Stacked on [`rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1)<br>Gated on Gates 1 & 2 | ✅ 100% (Suite 7) | ✅ **SUCCESS** (`Bci` #7 local, #6 remote) |
| **FEAT-3** | Binary Name Delegation & Prefix Sync (`binary_rule`) | `reprepro-updater`<br>`ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-rosdistro`<br>`upstream_a-release` | **`feat/package-prefix`** (`93ed2dc`)<br>**`feat/binary-naming-rule`** (`4062a66`)<br>`feat/binary-naming-rule`<br>`feat/binary-naming-rule`<br>`debian/vendor-upstream/resolute/upstream_a` | `master` (`refactor` `1e7aa5c`)<br>**`master`** (`7daa2b1`)<br>`rep159`<br>`main`<br>`master` | Wave 0 (`reprepro` $\to$ `refactor`)<br>Gated on Gates 1 & 2 + `reprepro` | ✅ 100% (6 unit tests) | ✅ **SUCCESS** (`Usrc` #11, `Ubin` #7) |
| **FEAT-4** | Formal Specification & Rationale in REP-159 Text | `KmoM88/reps` $\to$ `openrobotics/reps` | `feature/rep-159-binary-name-templating` (`83e4a3f`) | `openrobotics:rosdistro_extension` | [`reps#31`](https://github.com/openrobotics/reps/pull/31) (Merged)<br>[`reps#35`](https://github.com/openrobotics/reps/pull/35) (**OPEN**; feeds [#32](https://github.com/openrobotics/reps/pull/32)) | ✅ 100% (`binary_rule`) | ⚠️ Needs `install_rule` formal subsection |
| **FEAT-5** | Release Pipeline, Mirror Import & Sync (`reprepro` + Nginx) | `ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-testing` | `test/rep159-release-pipeline`<br>`rep159`<br>`main` | `test/rep159-install-prefixes`<br>`master`<br>`main` | Local testbed harness | ✅ 100% (APT active on :8088 with GPG) | ✅ **SUCCESS** (`Usrc` #10, `Ubin` #4, `Urel_sync` #4, `Bci` #4) |
| **FEAT-6** | Multi-Tier Chaining & Hybrid Topologies ($A \to B \to C$ & Diamond) | `rosdistro`<br>`ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-rosdistro`<br>`downstream_bin_a-release` | `feature/rep159-install-rule` (`db021b9`)<br>`feat/binary-naming-rule` (`4062a66`) + `rep159` (`9736140`)<br>`feat/stage3-diamond`<br>`feat/stage3-diamond`<br>`release/extendablebin/downstream_bin_a` | `feature/rep159-binary-naming-regex`<br>`master`<br>`feat/stage3-mixed`<br>`feat/stage3-mixed`<br>`upstream` | Gated on Gates 1 & 2 | ✅ Option A: 100% (#3)<br>✅ Option B: 100% (#13)<br>✅ Mixed: 100% (#2) | ✅ Option A: 100% (Remote #2)<br>✅ Option B: 100% (Remote #7)<br>✅ Mixed/Diamond: 100% (#1) |
| **FEAT-7** | Stage 4: `composable` Suite, `ros_workspace` Sourcing & Bloom | `bloom`<br>`ros_workspace`<br>`ros_workspace-release`<br>`upstream_{a,b,c}-release`<br>`rep159-rosdistro`<br>`ros_buildfarm_config` | `feat/rep159-rules-support` (`d6fdf9e`)<br>`feat/composable-underlay-chaining` (`032d161`) & `rep159-parent-chain` (`12f93e9`)<br>`debian/vendor-composable/resolute/ros_workspace`<br>`debian/vendor-composable/resolute/upstream_{a,b,c}`<br>`feat/composable-distro`<br>`feat/composable-distro` | `rep159` (`2877687`)<br>`main` (`db49f0a`)<br>`debian/vendor-composable`<br>`debian/vendor-composable`<br>`main`<br>`rep159` | `ros_workspace`: Wave 1 (reconcile)<br>`bloom`: Wave 2 (Gates 1 & 2) | ✅ 100% (5-step local pipeline) | ✅ **SUCCESS** (`Csrc` #5, `Cbin` #3, `Crel_sync` #5, `Cci` #3, #4) |
| **FEAT-8** | Stage 5: Cache Lifecycle & Hierarchy (`rosdistro_build_cache`) | `ros_buildfarm`<br>`rep159-rosdistro`<br>`ros_buildfarm_config` | `feat/cache-job-rep159` (`6f62d7b`)<br>`feat/cache-lifecycle-test`<br>`feat/cache-lifecycle-test` | `master` (`7daa2b1`)<br>`main`<br>`rep159` | Replaced upstream by Gate 1 APT (`python3-rosdistro >= 1.2.0`) | ✅ 100% Local Validation | ✅ **SUCCESS** (`cachebase` #18, `cachechild` #18) |
| **FEAT-9** | Stage 5: Automated Debian Packaging with REP-159 Bloom Fork | `bloom`<br>`downstream_bin_a-release` | `feat/rep159-rules-support` (`d6fdf9e`)<br>`debian/cachechild/resolute/downstream_bin_a` | `rep159` (`2877687`)<br>`upstream` | Wave 0 (`d6fdf9e` gpgSign fix)<br>Wave 2 (`bloom >= 0.15.0`) | ✅ 100% Generated & Verified | ✅ Pushed branch & tag to origin |

---

## 3. Core Implementation vs. Engineering Fixes vs. Pre-Release Overrides (Beyond `rosdistro`)

| Repository & Branch(es) | (A) Core Feature Commits | (B) Required Engineering Fixes (Committed + Pre-PR Actions) | (C) Pre-Release Overrides to Drop After Release Gate | Release Gate Prerequisite |
|---|---|---|---|---|
| **`reprepro-updater`**<br>`feat/package-prefix` (`93ed2dc`) | `93ed2dc`: `--package-prefix` in `scripts/sync_ros_packages.py` & `src/reprepro_updater/helpers.py` (`FilterFormula` & cleanup) | Target **`refactor`** branch on `ros-infrastructure/reprepro-updater` (`scripts/sync_ros_packages.py` lives on `refactor`, not `master`) | None (0 fork dependencies) | **Wave 0 (None)** — Jenkins sync jobs `git clone -b refactor` directly |
| **`rosdep`**<br>`rep159` (`3d52dad`) | `2d5a548`, `3d52dad`: `gbpdistro_support.py` delegates to `get_binary_package_name()` with `binary_import` fallback.<br>`07b6647`: Format 3 extended distro unit tests | **Pre-PR**: Cut clean branch off `master`; bump `rosdistro >= 1.2.0` (`setup.py`) & `python3-rosdistro-modules (>= 1.2.0)` (`stdeb.cfg`); add `binary_rule` test case in `test_rosdep_gbpdistro_support.py` | `a83d852`, `366891f`, `e88ba75`, `2b41634`, `b436f33`: Drop `KmoM88/rosdistro@feature/rep-2015-v3-parser` URL & `ROSDEP_LOCAL_DEV` from `setup.py` and `.github/workflows/ci.yaml` | **Wave 1** — Requires **Gate 1 (`rosdistro >= 1.2.0` PyPI + APT)**; unblocks **Gate 2 (`rosdep >= 0.27.0`)** |
| **`ros_workspace`**<br>`rep159-parent-chain` (`12f93e9`) & `feat/composable-underlay-chaining` (`032d161`) | `12f93e9` & `032d161`: Register `parent_prefix_path` resource when `ROS_WORKSPACE_PARENT_PREFIX_PATH` / `PARENT_PREFIX_PATH` is set | **Pre-PR**: Reconcile both branches to retain `12f93e9`'s multi-prefix `ament_package` discovery loop + root `SKIP_PARENT_PREFIX_PATH` default alongside `032d161`'s `PARENT_PREFIX_PATH` resource registration | None (pure `CMakeLists.txt`) | **Wave 1** (CMake independent); releasing child `.deb` requires **Gate 3 (`bloom >= 0.15.0`)** |
| **`bloom`**<br>`rep159` (`2877687`) + `feat/rep159-rules-support` (`d6fdf9e`) | `0189046`..`2877687` (`rep159`): `get_binary_import_parents()`, `ParentPrefixes` in `rules.em`, `get_ros_workspace_dependencies()`.<br>`1f62809`: `binary_rule` & `install_rule` in `rosdistro_api.py` & `rosdebian.py` + tests | **Committed**: `d6fdf9e` (`generator.py` `git tag -f -m` for `tag.gpgSign=true` — **Wave 0**).<br>**Pre-PR**: Fix `bloom/rosdistro_api.py:get_install_prefix()` to call `dist_file.get_install_prefix()` so regex `dict` `install_rule` does not silently fall back; bump `rosdistro >= 1.2.0` & `rosdep >= 0.27.0` in `setup.py`/`stdeb.cfg`; note Debian-first (`rosdebian.py`) scope | None in repo files | **Wave 2** — Requires **Gate 1 (`rosdistro >= 1.2.0`) + Gate 2 (`rosdep >= 0.27.0`)**; unblocks **Gate 3 (`bloom >= 0.15.0`)** |
| **`ros_buildfarm`**<br>`rep159` (`9736140`) + `feat/install-prefixes` (`4f4b059`) + `feat/binary-naming-rule` (`4062a66`) + `feat/cache-job-rep159` (`6f62d7b`) | **PR 3A (`rep159`)**: `52b51d8`, `9736140` (`create_workspace.py` walk & tests).<br>**PR 3B (`feat/*`)**: `006a4a1`, `80e1e0b`, `aa9f572` (`install_rule` & `ROS_BUILDFARM_PARENT_RESULT_SPACES`).<br>**PR 3C (`feat/*`)**: `857b025`, `61b8d29`, `ceaaef7`, `c907db2` (`binary_rule` delegation & `--package-prefix` sync) + bump `rosdistro >= 1.2.0` in `setup.py`/`stdeb.cfg` | **Wave 0 Standalone**: `ae8826b` (`wrapper/git.py` TLS retry); `2823cf1`/`199fd98`/`40231f3` (`jenkins.py` 403 view skip).<br>**Fold into PR 3B**: `dd2825e` (`build_and_install.py` empty `--parent-result-space` fallback); `12982be` & `2a869d8` (`workspace.py` pure-CMake `CMAKE_PREFIX_PATH` & multiarch `LD_LIBRARY_PATH` fallback).<br>**Fold into PR 3C**: `4062a66` (`release_job.py` skip inherited parent packages not in `dist_file.release_packages`); `3397a12` (`binarydeb_job.py`/`binaryrpm_job.py` renamed subfolder & assertion lookup).<br>**Pre-PR**: Combine `rep159` + `feat/*` commits onto fresh PR branches without rebasing active testbed branches | Drop tarball `pip3 install` blocks in 6 `*.Dockerfile.em` templates (`fc7b990`, `aa4d978`, `1fd12c0`, `4b3072b`, `68369e9`, `efcbab3`, `40231f3`, `4f4b059`, `6f62d7b`); revert `reprepro-updater` URL in `sync_packages_to_*_job.xml.em` (`c907db2`) back to `ros-infrastructure/reprepro-updater -b refactor`; revert `assignedNode` in `rosdistro_cache_job.xml.em` (`8c1f978`, `6f62d7b`) | **Wave 3** — Requires **Gate 1 + Gate 2 (in `ros_bootstrap` APT & PyPI) + `reprepro-updater:refactor` merge**; unblocks **Gate 4 (`ros_buildfarm >= 4.2.0`)** |

---

## 4. Detailed Feature Specifications

### FEAT-0: Baseline REP-159 MVP (Walk, ABI Guardrails, Format 3)
- **Problem**: Upstream tools had no concept of cross-distribution inheritance (`extends:`), dependency graph resolution across distribution boundaries, or ABI conflict prevention.
- **Solution**:
  - Implemented ROSDistro Format 3 schema parsing.
  - Implemented topological walk (`scripts/ci/create_workspace.py` commits `52b51d8`, `9736140` on `ros_buildfarm:rep159`) and ABI guardrails ensuring downstream distributions cannot silently mutate upstream package definitions.
- **Submodules & Branches**:
  - `rosdistro` (`rep159` @ `46a7580`), `rosdep` (`rep159` @ `3d52dad`), `ros_buildfarm` (`rep159` @ `9736140`), `ros_buildfarm_config` (`rep159`).
  - Collaborator variant: `rosdistro` branch `rep159-child-ros-workspace` (`4a89ac4`, `78c7db8`) allowing/requiring a `binary_import` child distribution to release its own `ros_workspace`.
- **Validation**: Local test suites 1 through 5 passed; baseline Jenkins release and CI pipelines executed successfully.

---

### FEAT-1: Binary Renaming Engine (`binary_rule`)
- **Problem**: `rosdistro` and `rosdep` rigidly enforced the `ros-{distro}-{package}` package naming convention.
- **Solution**:
  - Implemented `binary_rule` in `DistributionFile` and `ReleaseRepositorySpecification` supporting regular expressions (`search`, `replace`), dynamic variables (`{distro}`, `{package}`, `{origin_distro}`), and capture groups (`\1`).
  - Updated `rosdep` (`src/rosdep2/gbpdistro_support.py`) to delegate Debian/Ubuntu binary package name calculations directly to `rosdistro.get_binary_package_name()`.
- **Published GitHub Branches & PRs**:
  - `rep159-testing/rosdistro`: `feature/rep159-binary-naming-regex` (`3d301d6`) $\to$ `rep159` (Open PR: [`rep159-testing/rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1)).
  - `rep159-testing/rosdep`: `rep159` (`3d52dad`).
- **Validation**: Local test suite `tools/validate_binary_naming.py` (Suite 6 passed 100%).

---

### FEAT-2: Dynamic Installation Prefixes & Underlays (`install_rule`)
- **Problem**: Earlier experimental implementations hardcoded `/opt/ros/%s` for parent distributions under `binary_import`. If a parent distribution resided under `/opt/vendor` or `/usr` (e.g., Gazebo), builds failed.
- **Solution**:
  - `rosdistro`: Added `install_rule` at distribution, repository, and `extends` levels, supporting templates (`/opt/vendor/{distro}`) and regex search/replace, plus recursive `get_binary_import_underlays()`.
  - `ros_buildfarm`: Implemented `get_binary_import_underlays()`, `get_distribution_install_prefix()`, and dynamic parent result space resolution via `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
- **Published GitHub Branches**:
  - `rep159-testing/rosdistro`: `feature/rep159-install-rule` (`db021b9`, stacked on `feature/rep159-binary-naming-regex`).
  - `rep159-testing/ros_buildfarm`: `feat/install-prefixes` (`4f4b059`, branched from `origin/master` `7daa2b1`; includes temporary `create_workspace.Dockerfile.em` tarball overrides `40231f3`, `4f4b059` for pre-release testing).
  - `rep159-testing/ros_buildfarm`: `test/rep159-install-prefixes` *(integration branch for local CI)*.
- **Validation**: Local test suite `tools/validate_install_prefixes.py` (Suite 7 passed 100%). Verified in Jenkins with `Bci__nightly-release_ubuntu_resolute_amd64` Build #2 and #7 (**SUCCESS**) and remote Build #6 (**SUCCESS**).

---

### FEAT-3: Binary Name Delegation in `ros_buildfarm` & Prefix Sync in `reprepro-updater`
- **Problem**: In `ros_buildfarm/common.py`, `get_os_package_name()` and `get_os_package_name_prefix()` hardcoded `'ros-%s-%s'`, ignoring distribution `binary_rule` definitions. Release pipeline scripts omitted `dist_file`, child `binary_import` release views duplicated parent packages, and `reprepro-updater` hardcoded `ros-<distro>-*` filters.
- **Solution**:
  - `reprepro-updater` (`feat/package-prefix` @ `93ed2dc`): Added `-p / --package-prefix` for `FilterFormula` and cleanup.
  - `ros_buildfarm` (`feat/binary-naming-rule` @ `4062a66`): Delegated `get_os_package_name()` and `get_os_package_name_prefix()` to `dist_file`, propagated `--debian-package-name` and `--package-prefix`, fixed renamed subfolder lookups (`3397a12`), and filtered inherited parent packages out of child release job generation (`4062a66`).
- **Published GitHub Branches**:
  - `rep159-testing/reprepro-updater`: **`feat/package-prefix`** (`93ed2dc`, off `master`/`refactor` `1e7aa5c`).
  - `rep159-testing/ros_buildfarm`: **`feat/binary-naming-rule`** (`4062a66`, branched from `origin/master` `7daa2b1` incorporating `feat/install-prefixes`; carries temporary `*.Dockerfile.em` tarball overrides and `rep159-testing/reprepro-updater` URL until Gates 1 & 2 and `reprepro-updater:refactor` land).
  - `rep159-testing/ros_buildfarm`: `test/rep159-release-pipeline` *(local integration branch)*.
  - `rep159-testing/rep159-rosdistro`: `feat/binary-naming-rule`.
  - `rep159-testing/upstream_a-release`: `debian/vendor-upstream/resolute/upstream_a` (tag `debian/vendor-upstream-upstream-a_0.1.0-1_resolute`).
- **Validation**: Unit tests `test/test_binary_naming_rule.py` (6/6 tests passed). Jenkins builds `Usrc` #11 and `Ubin` #7 in **SUCCESS**.

---

### FEAT-4: Formal Specification & Rationale in REP-159 Text
- **Problem**: REP-159 required documenting the design explorations for binary package name transformation, rationale for choosing built-in Regex (`re.sub`) over external templating engines (EmPy, Jinja2), and formalizing installation prefix rules (`install_rule`).
- **Solution & Current Status**:
  - Merged initial binary transformation draft via [`openrobotics/reps#31`](https://github.com/openrobotics/reps/pull/31) into `openrobotics:rosdistro_extension`.
  - Opened [`openrobotics/reps#35`](https://github.com/openrobotics/reps/pull/35) (`KmoM88:feature/rep-159-binary-name-templating` @ `83e4a3f` $\to$ `openrobotics:rosdistro_extension`, feeding [`openrobotics/reps#32`](https://github.com/openrobotics/reps/pull/32)) documenting design explorations, zero-dependency regex rationale, and `binary_rule` under `binary_import`.
  - **Remaining Spec Addition**: Formalize the `install_rule` schema and fallback precedence subsection in `_posts/rep-0159:2026.md` (currently referenced only briefly on line 320).
- **Published GitHub Branches**:
  - `KmoM88/reps`: `feature/rep-159-binary-name-templating` (`83e4a3f`).

---

### FEAT-5: Release Pipeline, Reprepro APT Mirror & Target Switching
- **Problem**: Validating complete release pipelines (source $\rightarrow$ binarydeb $\rightarrow$ APT repository $\rightarrow$ snapshot) locally without requiring write permissions to official OSRF servers (`repo.ros2.org`).
- **Solution**:
  - Deployed a dedicated local APT server on Docker host (`192.168.30.202:8088`) with `reprepro` and `nginx:alpine` serving `resolute` suites (`building`, `shadow-fixed`, `main`).
  - Configured GPG repository signing (`Local ROS Buildfarm <buildfarm@local>`) and published public key via HTTP.
  - Updated `submodules/ros_buildfarm_config/index-local.yaml` to reference the local mirror.
  - Created `scripts/switch_target_farm.sh` to seamlessly switch between local and remote (`build.test.ros2.org`) testfarms.
- **Published GitHub Branches**:
  - `submodules/ros_buildfarm`: `test/rep159-release-pipeline`
  - `submodules/ros_buildfarm_config`: Branch `rep159`
- **Validation**: Verified end-to-end package promotion: `Usrc` #10 $\to$ `Ubin` #4 $\to$ `Urel_sync` #4 $\to$ `Bci` #4.

---

### FEAT-6: Multi-Tier Chaining & Hybrid Topologies (Stages 1-3)
- **Problem**: Validating cross-distribution extension behavior across complex topologies: multi-tier source chaining ($A \to B \to C$), multi-tier binary chaining via `binary_import`, hybrid distributions (`--ignore-src`), and multi-parent convergent diamond DAGs.
- **Solution**:
  - **Option A (Chained Source Rebuild)**: Validated multi-tier compilation of 5 packages across root and overlay distributions (`upstream_{a,b,c}`, `downstream_bin_a`, `downstream_chain_a`).
  - **Option B (Chained Binary Import)**: Fixed underlay fallback in `build_and_install.py` (commit `dd2825e`), CMake prefix discovery in `workspace.py` (commit `12982be`), and runtime `LD_LIBRARY_PATH` multiarch exports (commit `2a869d8`). `downstream_chain_a` consumed pre-built debians from APT and passed unit tests 100% green.
  - **Topology 2 (Hybrid Binary + Source & Diamond DAG)**: Validated workspace package override (`--ignore-src`) where `upstream_c` compiled from source while `downstream_bin_a` was installed from APT binaries, plus multi-parent deduplication in `extendablediamond`.
- **Published GitHub Branches**:
  - `submodules/ros_buildfarm`: `feat/binary-naming-rule` (`4062a66`) & `rep159` (`9736140`)
  - `submodules/ros_buildfarm_config`: `feat/stage3-binary-chained`, `feat/stage3-mixed`, `feat/stage3-diamond`
  - `submodules/rep159-rosdistro`: `feat/stage3-binary-chained`, `feat/stage3-mixed`, `feat/stage3-diamond`
- **Validation**:
  - Option A: Local Build #3 **SUCCESS**, Remote Build #2 **SUCCESS**.
  - Option B: Local Build #13 **SUCCESS**, Remote Build #7 **SUCCESS**.
  - Hybrid & Diamond Topologies: Local Build #2 **SUCCESS**, Remote Builds #1 **SUCCESS**.

---

### FEAT-7: Stage 4 — Composable Suite, `ros_workspace` Sourcing & Bloom Integration
- **Problem**: Stages 1 through 3 relied on pure CMake packages, requiring fallback path injection (`CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`). A production ROS 2 distribution requires `ros_workspace` to generate `/opt/ros/<distro>/setup.sh`, chain underlays via `.dsv` environment hooks, and have Bloom honor `binary_rule` and `install_rule`.
- **Solution**:
  - **Bloom Fork (`rep159-testing/bloom`)**: Branch `feat/rep159-rules-support` (`d6fdf9e`, stacked on `rep159` @ `2877687`) enables dynamic package and dependency naming from `rosdistro.get_binary_package_name()`, generates `install_rule` prefixes and `ParentPrefixes` sourcing in `debian/rules`. *(Pre-PR fix noted: delegate `get_install_prefix()` to `dist_file.get_install_prefix()` for regex dict `install_rule` support).*
  - **Underlay Chaining in `ros_workspace`**: Branches `rep159-parent-chain` (`12f93e9`) and `feat/composable-underlay-chaining` (`032d161`) chain parent underlay paths into the `composable` / `composablebin` environment *(to be reconciled into a single upstream PR preserving parent `ament_package` discovery and root `SKIP_PARENT_PREFIX_PATH` default)*.
  - **Hermetic Release & CI**: Packaged and installed `vendor-composable-ros-workspace_1.0.4-1resolute` into `/opt/ros/composable`, and validated `Cci__nightly-release` and `Cci__binary-import` executing `. /opt/ros/composable/setup.sh && colcon build` natively.
- **Published GitHub Branches**:
  - `submodules/bloom`: `feat/rep159-rules-support` (`d6fdf9e`, base `rep159` @ `2877687`)
  - `submodules/ros_workspace`: `feat/composable-underlay-chaining` (`032d161`) & `rep159-parent-chain` (`12f93e9`)
  - `submodules/ros_workspace-release`: `debian/vendor-composable/resolute/ros_workspace`
  - `submodules/upstream_{a,b,c}-release`: `debian/vendor-composable/resolute/upstream_{a,b,c}`
  - `submodules/downstream_bin_a-release`: `debian/vendor-composablebin/resolute/downstream_bin_a`
  - `submodules/rep159-rosdistro`: `feat/composable-distro`
  - `submodules/ros_buildfarm_config`: `feat/composable-distro`
- **Validation**: 5-step local pipeline 100% **SUCCESS** (`Csrc` #5, `Cbin` #3, `Crel_sync` #5, `Cci` #3, `Cci` #4).

---

### FEAT-8: Stage 5 — Distribution Cache Lifecycle & Hierarchical Inheritance
- **Problem**: `rosdistro_build_cache` executes in a task container (`rosdistro_cache_task.Dockerfile.em`) built from Ubuntu Focal APT packages that lacked ROSDistro Format 3 support prior to Release Gate 1. Operational mechanics for cache publishing, hierarchy isolation, and manifest change detection required systematic validation.
- **Solution**:
  - Validated `rosdistro_build_cache` with the REP-159 `rosdistro` engine on testbed branch `feat/cache-job-rep159` (`6f62d7b`). *(Upstream, once Gate 1 publishes `python3-rosdistro >= 1.2.0` to `ros_bootstrap` APT across `focal..resolute`, bumping `stdeb.cfg` / `setup.py` in `ros_buildfarm` replaces the temporary tarball `pip` install and `assignedNode` override completely).*
  - Established minimal 2-tier hierarchy: `cachebase` (root) $\to$ `cachechild` (overlay with `extends: cachebase`).
  - Validated automatic publication of `<distro>-cache.yaml.gz` via SSH to the APT/Nginx mirror.
  - Validated parent cache inheritance and boundary isolation: `cachechild_rosdistro-cache` loaded `cachebase-cache.yaml.gz`, resolved cross-distribution dependencies, and stripped parent packages (`- REMOVE upstream_{a,b,c}`) ensuring upstream ABI immutability.
  - Validated cache invalidation: bumping `upstream_a` version (0.1.0 $\to$ 0.1.1) triggered selective manifest updates and automated Groovy post-build reconfigure detection.
- **Published GitHub Branches**:
  - `submodules/ros_buildfarm`: `feat/cache-job-rep159` (`6f62d7b`)
  - `submodules/rep159-rosdistro`: `feat/cache-lifecycle-test`
  - `submodules/ros_buildfarm_config`: `feat/cache-lifecycle-test`
- **Validation**: Jenkins jobs `cachebase_rosdistro-cache` (Builds #7..#18) and `cachechild_rosdistro-cache` (Builds #4..#18) in **SUCCESS** 100%.

---

### FEAT-9: Stage 5 — Automated Debian Packaging Generation with Bloom
- **Problem**: Standard `bloom` hardcodes Debian package naming (`ros-<distro>-<pkg>`) and installation prefixes (`/opt/ros/<distro>`), requiring manual patching for custom distributions.
- **Solution**:
  - In `submodules/bloom` on branch `feat/rep159-rules-support` (`d6fdf9e`, stacked on `rep159` @ `2877687`):
    - Updated `bloom/rosdistro_api.py` and `bloom/generators/rosdebian.py` to evaluate `rosdistro.get_binary_package_name()` for package names and dependencies.
    - Parameterized `CMAKE_INSTALL_PREFIX` and `PKG_CONFIG_PATH` based on `install_rule` and `ParentPrefixes`.
    - Injected chained underlay sourcing loops into `debian/templates/{ament_cmake,cmake}/rules.em`.
    - Added `-m` message flag to `git tag -f` in `bloom/generators/debian/generator.py` (`d6fdf9e`) to support environments with `tag.gpgSign=true`.
  - Executed `git-bloom-generate rosdebian cachechild --os-name ubuntu --distros resolute -p release/extendablebin` on `downstream_bin_a-release`:
    - `debian/control`: Generated `Package: vendor-cachechild-downstream-bin-a` with `Depends: ..., vendor-cachebase-upstream-c, vendor-cachechild-ros-workspace`.
    - `debian/rules`: Sourced `. /opt/ros/cachebase/setup.sh`, set `-DCMAKE_INSTALL_PREFIX="/opt/ros/cachechild"`, and chained `PKG_CONFIG_PATH`.
- **Published GitHub Branches**:
  - `submodules/bloom`: `feat/rep159-rules-support` (`d6fdf9e`)
  - `submodules/downstream_bin_a-release`: `debian/cachechild/resolute/downstream_bin_a` (tag `debian/vendor-cachechild-downstream-bin-a_0.2.0-0_resolute`)

---

## 5. Jenkins Execution Log (Local Buildfarm)

| Job | Build # | Date | Tested Branch | Result | Execution Notes |
|:---|:---:|:---:|:---|:---:|:---|
| `Uci__nightly-release...` | #4 | 2026-10-16 | `rep159` | **SUCCESS** | Upstream baseline CI verification. |
| `Uci__source-branches...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | Bootstrap source build validation. |
| `Uci__release-branches...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | Release tag dependency walk validation. |
| `Sci__nightly-release...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | `source_rebuild` crosses distribution boundary and compiles all packages. |
| `Bci__nightly-release...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | `binary_import` with hardcoded underlay prefix. |
| `Bci__nightly-release...` | #2 | 2026-10-17 | `test/rep159-install-prefixes`<br>`feature/rep159-install-rule` | **SUCCESS** | **FEAT-2 validated**: Dynamic underlay resolution via `ROS_BUILDFARM_PARENT_RESULT_SPACES`. |
| `Usrc_uR__upstream_a__ubuntu_resolute__source` | #1 | 2026-10-17 | `feat/binary-naming-rule` | **FAILURE** | Failed due to missing Format 3 parser support in release template. |
| `Usrc_uR__upstream_a__ubuntu_resolute__source` | #10 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Sourcedeb built, transferred via SSH, and ingested into `building` repo. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #4 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Binary deb and dbgsym built and ingested into `building` repo. |
| `Usrc_uR__upstream_b__ubuntu_resolute__source` | #1 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | `upstream_b` sourcedeb ingested into `building`. |
| `Ubin_uR64__upstream_b__ubuntu_resolute_amd64__binary` | #1 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | `upstream_b` binary deb built and ingested into `building`, resolving dependency `upstream_a`. |
| `Usrc_uR__upstream_c__ubuntu_resolute__source` | #1 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | `upstream_c` sourcedeb ingested into `building`. |
| `Ubin_uR64__upstream_c__ubuntu_resolute_amd64__binary` | #2 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | `upstream_c` binary deb built and ingested into `building`, resolving deps `upstream_b` and `upstream_a`. |
| `Urel_sync-packages-to-testing_resolute_amd64` | #4 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Successful synchronization; `ros-upstream-upstream-a`, `-b`, and `-c` published to `testing`. |
| `Bci__nightly-release_ubuntu_resolute_amd64` | #4 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | **PHASE 2 VALIDATED:** `downstream_bin_a` installed upstream binaries from `testing`, compiled, and passed tests 100% green. |
| `Usrc_uR__upstream_a__ubuntu_resolute__source` | #11 | 2026-10-19 | `feat/binary-naming-rule`<br>`test/rep159-release-pipeline` | **SUCCESS** | **FEAT-3 sourcedeb validated**: Built and imported `vendor-upstream-upstream-a 0.1.0-1resolute` into `building`. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #5 | 2026-10-19 | `test/rep159-release-pipeline` | **FAILURE** | Failed locating .dsc because `binarydeb_job.py` omitted `dist_file` in download step. Fixed in commit `3397a12`. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #6 | 2026-10-19 | `test/rep159-release-pipeline` | **FAILURE** | Failed resolving sourcedeb because `target_repository` pointed to remote OSRF instead of local mirror. Fixed via `release-build-local.yaml`. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #7 | 2026-10-19 | `feat/binary-naming-rule`<br>`test/rep159-release-pipeline` | **SUCCESS** | **FEAT-3 binarydeb validated**: Downloaded local sourcedeb, built `vendor-upstream-upstream-a_0.1.0-1resolute..._amd64.deb` and dbgsym, imported 100% green. |
| `Urel_sync-packages-to-testing_resolute_amd64` | #8 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Successful sync; `vendor-upstream-upstream-a` promoted to `testing`. |
| `Bci__nightly-release_ubuntu_resolute_amd64` | #6 | 2026-10-19 | `feat/install-rule`<br>`test/rep159-release-pipeline` | **FAILURE** | `generate_install_lists.py` KeyError: `upstream/distribution.yaml` inherited global `binary_rule` renaming `upstream_c`, but APT only hosted `ros-upstream-upstream-c`. |
| `Bci__nightly-release_ubuntu_resolute_amd64` | #7 | 2026-10-19 | `feat/install-rule`<br>`test/rep159-release-pipeline` | **SUCCESS** | **Stage 3 / FEAT-2 validated**: Dynamic injection of `ROS_BUILDFARM_PARENT_RESULT_SPACES=/opt/vendor/upstream`. Colcon built `downstream_bin_a` and passed tests 100% green. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #3 | 2026-10-20 | `feat/stage3-chained-extensions` | **SUCCESS** | **Stage 3 / Option A Validated Locally**: Complete multi-package build across all 5 source repos in colcon workspace. All GoogleTest suites passed 100% green. |
| `Esrc_uR__downstream_bin_a__ubuntu_resolute__source` | #1 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | **Stage 3 / Option B Sourcedeb**: Built and published `ros-extendablebin-downstream-bin-a_0.2.0-1resolute.dsc` to `building`. Automatically triggered binarydeb. |
| `Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary` | #1 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | **Stage 3 / Option B Binarydeb**: Installed `vendor-extendable-upstream-c` from local APT, built binary deb under `/opt/ros/extendablebin`, ingested to `building`. |
| `Erel_sync-packages-to-testing_resolute_amd64` | #9 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | Successful sync; `ros-extendablebin-downstream-bin-a` promoted to local `testing` repository. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #9 | 2026-10-20 | `feat/stage3-binary-chained` | **FAILURE** | APT installed binaries cleanly. Failed in `colcon build` because `build_and_install.py` did not fall back to `get_default_parent_result_spaces()` on empty `--parent-result-space`. Fixed in commit `dd2825e`. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #10 | 2026-10-20 | `feat/stage3-binary-chained` | **FAILURE** | Docker layer caching in runner reused image without `setup.sh` in underlays without exported environment variables. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #11 | 2026-10-20 | `feat/stage3-binary-chained` | **FAILURE** | Pure CMake packages under `/opt/ros/extendablebin` lacked `setup.sh`; `workspace.py` did not export `CMAKE_PREFIX_PATH`. Fixed in commit `12982be`. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #12 | 2026-10-20 | `feat/stage3-binary-chained` | **UNSTABLE** | **Build 100% SUCCESS**: Found `downstream_bin_a` and compiled `downstream_chain_a`. Runtime test failed due to missing `LD_LIBRARY_PATH`. Fixed in commit `2a869d8`. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #13 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | **STAGE 3 OPTION B (CHAINED BINARY IMPORT) 100% VALIDATED**: Dynamic injection of `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH`, and multiarch `LD_LIBRARY_PATH`. Clean APT install, build, link, and test pass (1/1 green). |
| `Eci__mixed-chain_ubuntu_resolute_amd64` | #1 | 2026-10-21 | `feat/stage3-mixed` | **FAILURE** | Failed in rosdep: re-declaration of `upstream_c` in `extendablemixed` violated REP-159 ABI immutability. Resolved by clean inheritance without distribution collision. |
| `Eci__mixed-chain_ubuntu_resolute_amd64` | #2 | 2026-10-21 | `feat/stage3-mixed` | **SUCCESS** | **STAGE 3 TOPOLOGY 2 (HYBRID BINARY + SOURCE) 100% VALIDATED**: `downstream_bin_a` installed from APT; `upstream_c` rebuilt in workspace (`--ignore-src`). Compiled, linked, and passed 2/2 tests green. |
| `Csrc_uR__ros_workspace__ubuntu_resolute__source` | #5 | 2026-10-28 | `debian/vendor-composable/resolute/ros_workspace` | **SUCCESS** | **Stage 4 / FEAT-7**: Built sourcedeb `vendor-composable-ros-workspace_1.0.4-1resolute.dsc` with prefix `/opt/ros/composable` and exported to `building`. |
| `Cbin_uR64__ros_workspace__ubuntu_resolute_amd64__binary` | #3 | 2026-10-28 | `debian/vendor-composable/resolute/ros_workspace` | **SUCCESS** | **Stage 4 / FEAT-7**: Built `vendor-composable-ros-workspace_1.0.4-1resolute_amd64.deb` establishing environment layout, `.dsv` hooks, and underlay chaining to `/opt/ros/upstream`. |
| `Csrc_uR__upstream_a__ubuntu_resolute__source` | #1 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_a` | **SUCCESS** | Built sourcedeb `vendor-composable-upstream-a_0.1.0-1resolute.dsc` and ingested into `building`. |
| `Cbin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #2 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_a` | **SUCCESS** | Built and ingested `vendor-composable-upstream-a_0.1.0-1resolute_amd64.deb` into `building`. |
| `Csrc_uR__upstream_b__ubuntu_resolute__source` | #1 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_b` | **SUCCESS** | Built sourcedeb `vendor-composable-upstream-b_0.1.0-1resolute.dsc` and ingested into `building`. |
| `Cbin_uR64__upstream_b__ubuntu_resolute_amd64__binary` | #3 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_b` | **SUCCESS** | Built and ingested `vendor-composable-upstream-b_0.1.0-1resolute_amd64.deb` into `building`. |
| `Csrc_uR__upstream_c__ubuntu_resolute__source` | #1 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_c` | **SUCCESS** | Built sourcedeb `vendor-composable-upstream-c_0.1.0-1resolute.dsc` and ingested into `building`. |
| `Cbin_uR64__upstream_c__ubuntu_resolute_amd64__binary` | #3 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_c` | **SUCCESS** | Built and ingested `vendor-composable-upstream-c_0.1.0-1resolute_amd64.deb` into `building`. |
| `Crel_sync-packages-to-testing_resolute_amd64` | #5 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | Promoted 4 debian packages from `building` to `testing` (`vendor-composable-ros-workspace` and `vendor-composable-upstream-{a,b,c}`). |
| `Cci__nightly-release_ubuntu_resolute_amd64` | #3 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | **STAGE 4 ROOT DISTRO VALIDATED**: APT installed `vendor-composable-ros-workspace` from `testing`. Colcon compiled `upstream_{a,b,c}` natively sourcing `. /opt/ros/composable/setup.sh`. All tests passed 100% green. |
| `Csrc_uR__downstream_bin_a__ubuntu_resolute__source` | #2 | 2026-10-28 | `debian/vendor-composablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 4 / Composablebin Sourcedeb**: Built sourcedeb `vendor-composablebin-downstream-bin-a_0.2.0-1resolute.dsc` and ingested to `building`. |
| `Cbin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary` | #1 | 2026-10-28 | `debian/vendor-composablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 4 / Composablebin Binarydeb**: Installed `vendor-composable-upstream-c` from APT, compiled under prefix `/opt/ros/composablebin`, generated binary deb and ingested to `building`. |
| `Crel_sync-packages-to-testing_resolute_amd64` | #6 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | Successful sync; `vendor-composablebin-downstream-bin-a` promoted to `testing` with filter `Package (% vendor-composablebin-*)`. |
| `Cci__binary-import_ubuntu_resolute_amd64` | #4 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | **STAGE 4 COMPOSABLEBIN NATIVE UNDERLAY SOURCING 100% VALIDATED**: Installed `vendor-composable-ros-workspace` from `testing`. Sourced `. /opt/ros/composable/setup.sh` across all colcon build and test phases. 100% tests green. |
| `cachebase_rosdistro-cache` | #7..#18 | 2026-10-28 | `feat/cache-lifecycle-test`<br>`feat/cache-job-rep159` | **SUCCESS** | **Stage 5 / FEAT-8**: Built `cachebase-cache.yaml.gz`, transferred via SSH to mirror, and validated manifest update detection (0.1.0 $\to$ 0.1.1). |
| `cachechild_rosdistro-cache` | #4..#18 | 2026-10-28 | `feat/cache-lifecycle-test`<br>`feat/cache-job-rep159` | **SUCCESS** | **Stage 5 / FEAT-8**: Queried parent cache `cachebase-cache.yaml.gz`, resolved dependencies, stripped parent packages (`- REMOVE upstream_{a,b,c}`), and published `cachechild-cache.yaml.gz`. |

---

## 6. Jenkins Execution Log (Remote Testfarm `build.test.ros2.org`)

| Job | Build # | Tested Branch | Result | Execution Notes |
|:---|:---:|:---|:---:|:---|
| `Uci__nightly-release...` | #3 | `feat/binary-naming-rule` | **SUCCESS** | 933s. Upstream baseline CI OK. |
| `Uci__source-branches...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 953s. Bootstrap source build OK. |
| `Uci__release-branches...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 951s. Release tag dependency walk OK. |
| `Sci__nightly-release...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 913s. `source_rebuild` OK. |
| `Bci__nightly-release...` | #4 | `feat/binary-naming-rule` | **FAILURE** | 483s. `binary_import` failed due to missing underlay injection (resolved in FEAT-2). |
| `Usrc_uR__upstream_a...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | Built and published `vendor-upstream-upstream-a_0.1.0-1resolute.dsc` to `building`. |
| `Ubin_uR64__upstream_a...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 4m56s. Built and imported `vendor-upstream-upstream-a_0.1.0-1resolute_amd64.deb` to `building`. Triggered `Urel_import-package` #16 (**SUCCESS**). |
| `Bci__nightly-release...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **FAILURE** | 14m11s. Injected `/opt/vendor/upstream` but remote `.deb` files in OSRF testing reside under `/opt/ros/upstream`. |
| `Sci__nightly-release...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Complete compilation of `source_rebuild` on `feat/install-prefixes`. |
| `Uci__nightly-release...` | #4 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Upstream baseline CI OK on `feat/install-prefixes`. |
| `Uci__source-branches...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Bootstrap source build OK on `feat/install-prefixes`. |
| `Uci__release-branches...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Release tag walk OK on `feat/install-prefixes`. |
| `Bci__nightly-release...` | #6 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Reconfigured with `install_rule: /opt/ros/{distro}` matching binary package prefix. Injected `/opt/ros/upstream`, resolved `upstream_cConfig.cmake`, compiled, and passed tests 100% green. |
| `Usrc_uR__upstream_b...` | #5 | `feat/binary-naming-rule` | **SUCCESS** | Published `vendor-upstream-upstream-b_0.1.0-1resolute.dsc` to `building`. |
| `Ubin_uR64__upstream_b...` | #8 | `feat/binary-naming-rule` | **SUCCESS** | Fixed dependency in `debian/control` without alternative pipe. Built and imported `vendor-upstream-upstream-b_0.1.0-1resolute_amd64.deb` into `building`. |
| `Usrc_uR__upstream_c...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | Built and published `vendor-upstream-upstream-c_0.1.0-1resolute.dsc` into `building`. |
| `Ubin_uR64__upstream_c...` | #9 | `feat/binary-naming-rule` | **SUCCESS** | Built and imported `vendor-upstream-upstream-c_0.1.0-1resolute_amd64.deb` into `building` resolving dependencies of `vendor-upstream-upstream-b` and `-a`. |
| `Urel_sync-packages-to-testing_resolute_amd64` | #10 | `feat/binary-naming-rule` | **SUCCESS** | Package synchronization criteria verified: confirmed availability in `building` of `vendor-upstream-upstream-{a,b,c}` (`All required binary packages are available`). |
| `Eci__chained-import_ubuntu_resolute_amd64` | #2 | `feat/stage3-chained-extensions` | **SUCCESS** | Multi-tier chained CI (Option A: `source_rebuild`) 100% successful on remote testfarm (`build.test.ros2.org`). Cloned and compiled 5 packages in cascade (`upstream_{a,b,c}`, `downstream_bin_a`, `downstream_chain_a`), passing all unit tests. |
| `Esrc_uR__downstream_bin_a__ubuntu_resolute__source` | #1 | `debian/extendablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 3B Remote Sourcedeb**: Built and published `ros-extendablebin-downstream-bin-a_0.2.0-1resolute.dsc` to OSRF `building`. |
| `Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary` | #1 | `debian/extendablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 3B Remote Binarydeb**: Consumed `vendor-extendable-upstream-c` from APT, built `ros-extendablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb`, and ingested to `building`. |
| `Erel_sync-packages-to-testing_resolute_amd64` | #7 | `feat/stage3-binary-chained` | **SUCCESS** | **Stage 3B Remote Sync**: Promoted `ros-extendablebin-downstream-bin-a` to public repository `http://repo.test.ros2.org/ubuntu/testing`. |
| `Eci__mixed-chain_ubuntu_resolute_amd64` | #1 | `feat/stage3-mixed` | **SUCCESS** | **Stage 3 Topology 2 (Hybrid Binary + Source) Remote**: Hybrid CI successful on public `build.test.ros2.org` runners. Installed `ros-extendablebin-downstream-bin-a` from APT, built `upstream_c` and `downstream_chain_a` in workspace, and executed 2/2 test suites green. |
