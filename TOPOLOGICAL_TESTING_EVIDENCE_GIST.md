# REP-159: Comprehensive Validation & Evidence Suite

This document establishes the empirical validation evidence, architectural models, branch matrices, and job configurations across the three core validation phases of the **[REP 159](https://github.com/openrobotics/reps/pull/32)** test campaign.

---

## Thematic Block 1: Binary Renaming, Custom Install Paths & Release Pipeline

### Architecture & Pipeline Overview

```mermaid
graph LR
    subgraph Spec [Distribution Metadata: Format 3]
        BR["binary_rule: vendor-{distro}-{package}"]
        IR["install_rule: /opt/ros/{distro}"]
    end

    subgraph ReleasePipeline [Hermetic Release Pipeline]
        SRC["Source Job: Esrc_uR__*<br/>Generates .dsc with custom name"]
        BIN["Binary Job: Ebin_uR64__*<br/>Builds .deb with custom prefix"]
        SYNC["Sync Job: Erel_sync-*<br/>Reprepro package prefix filter"]
        
        SRC -->|triggers| BIN
        BIN -->|imports to building| SYNC
    end

    subgraph Repositories [APT Repositories]
        BUILDING["reprepro: building<br/>vendor-extendable-upstream-*"]
        TESTING["reprepro: testing<br/>vendor-extendable-upstream-*"]
        
        SYNC -->|promotes| TESTING
    end

    Spec --> ReleasePipeline
```

### Feature Mechanics

1. **Binary Name Templating (`binary_rule`)**:
   - REP-159 extends `rosdistro` distribution specifications with a Format 3 `binary_rule` dictionary containing `search` and `replace` regex directives, `{distro}`, `{package}` variables, and regex capture groups (`\1`).
   - `rosdistro.get_binary_package_name()` deterministically converts ROS package names (e.g., `upstream_a`) to customized OS binary packages (e.g., `vendor-extendable-upstream-a`).
   - `ros_buildfarm` release jobs query `dist_file.get_binary_package_name()` to format source package tarballs (`.orig.tar.gz`), Debian source control files (`.dsc`), and binary archives (`.deb`).

2. **Custom Installation Prefix Resolution (`install_rule`)**:
   - ROS distributions and repositories declare parameterized install locations (e.g., `/opt/ros/{distro}` or `/opt/vendor/{distro}`).
   - Release jobs pass `CMAKE_INSTALL_PREFIX` to build processes, ensuring binaries install into their declared hierarchy.

3. **Reprepro Package Filter Synchronization & Ingestion Invariants**:
   - `reprepro-updater` filters incoming packages using `--package-prefix <prefix>`.
   - Prevents binary collisions and ensures only vendor-specific packages matching the declared naming prefix are promoted from `building` to `testing`.
   - In shared flat APT pools, prefix isolation guarantees that downstream packages do not accidentally overwrite or shadow packages from parallel vendor stacks.

### Stage 1 Upstream PR Architecture & Release Gating

Upstreaming Stage 1 features follows a release-gated dependency progression across Open Robotics repositories to prevent broken dependencies during Debian packaging and CI:

```mermaid
flowchart TD
    subgraph Wave0 ["Wave 0: Unencumbered Baseline PRs"]
        direction TB
        REPS["openrobotics/reps#35: binary_rule & install_rule specs"]
        REPREPRO["reprepro-updater: feat/package-prefix (targets refactor)"]
        ROSDISTRO["rosdistro PRs: binary_rule & feat/rep159-install-rule"]
        BF_STANDALONE["ros_buildfarm: Standalone TLS & Jenkins 403 fixes"]
    end

    subgraph Gate1 ["Release Gate 1"]
        G1{{"rosdistro >= 1.2.0 (PyPI + ros_bootstrap APT)"}}
    end

    subgraph Wave1 ["Wave 1: Client Resolution & Workspace Chaining"]
        direction TB
        ROSDEP["rosdep PR: feat/rep159-binary-lookup (clean off master)"]
        WORKSPACE["ros_workspace: feat/rep159-parent-chaining (clean off main)"]
    end

    subgraph Gate2 ["Release Gate 2 & 2B"]
        G2{{"rosdep >= 0.27.0 (PyPI + ros_bootstrap APT)"}}
        G2B{{"ros_workspace >= 1.0.4 (ROS 2 distros)"}}
    end

    subgraph Wave2 ["Wave 2: Packaging Generator (Requires Gates 1 & 2)"]
        BLOOM["bloom: feat/rep159-rules-support (clean off master)"]
    end

    subgraph Gate3 ["Release Gate 3"]
        G3{{"bloom >= 0.15.0 (PyPI + ros_bootstrap APT)"}}
    end

    subgraph Wave3 ["Wave 3: Buildfarm Orchestration (Requires Gates 1 & 2)"]
        direction TB
        BF1["ros_buildfarm: feat/rep159-binary-naming (PR 3C)"]
        BF2["ros_buildfarm: feat/rep159-workspace-walk (PR 3A)"]
        BF3["ros_buildfarm: feat/rep159-underlays (PR 3B)"]
    end

    subgraph Gate4 ["Release Gate 4"]
        G4{{"ros_buildfarm >= 4.2.0 (PyPI + ros_bootstrap APT)"}}
    end

    ROSDISTRO --> G1
    G1 --> ROSDEP --> G2
    WORKSPACE --> G2B
    G1 --> BLOOM
    G2 --> BLOOM
    BLOOM --> G3
    G1 --> Wave3
    G2 --> Wave3
    REPREPRO --> Wave3
    BF_STANDALONE -.-> Wave3
    Wave3 --> G4
```

#### Phased Release-Gate Progression Timeline (Gantt Schedule)

```mermaid
gantt
    title REP-159 Phased Upstreaming & Release-Gate Progression Timeline
    dateFormat YYYY-MM-DD
    axisFormat %b %Y

    section Wave 0 (Specs & Standalone)
    reps#35 (binary_rule lowercase spec)    :done, m0_reps, 2026-01-01, 2026-02-15
    reps (install_rule spec extension)      :done, m0_reps_inst, 2026-01-15, 2026-02-28
    reprepro-updater (--package-prefix)     :done, m0_reprepro, 2026-02-01, 2026-03-01
    Standalone fixes (TLS, 403, gpgSign)    :done, m0_fixes, 2026-02-01, 2026-03-01

    section Milestone 1 (rosdistro)
    rosdistro Format 3 & binary_rule (#1)   :active, m1_rd_pr, 2026-02-15, 2026-03-20
    rosdistro feat/rep159-install-rule      :active, m1_inst_pr, 2026-02-25, 2026-03-25
    RELEASE GATE 1 (rosdistro >= 1.2.0)     :milestone, m1_gate, 2026-03-25, 0d

    section Milestone 2 (rosdep & ros_workspace)
    rosdep feat/rep159-binary-lookup        :active, m2_rdep, after m1_gate, 30d
    RELEASE GATE 2 (rosdep >= 0.27.0)       :milestone, m2_gate, after m2_rdep, 0d
    ros_workspace feat/rep159-parent-chain  :active, m2_ws, 2026-03-01, 2026-03-31
    RELEASE GATE 2B (ros_workspace >= 1.0.4):milestone, m2b_gate, after m2_ws, 0d

    section Milestone 3 (bloom)
    bloom feat/rep159-rules-support         :active, m3_bloom, after m2_gate, 30d
    RELEASE GATE 3 (bloom >= 0.15.0)        :milestone, m3_gate, after m3_bloom, 0d

    section Milestone 4 (ros_buildfarm)
    ros_buildfarm PR 3A (workspace-walk)    :active, m4_3a, after m2_gate, 20d
    ros_buildfarm PR 3B (dynamic underlays) :active, m4_3b, after m4_3a, 20d
    ros_buildfarm PR 3C (binary-naming)     :active, m4_3c, after m4_3b, 20d
    ros_buildfarm PR 5 (cache-job-rep159)   :active, m4_cache, after m4_3c, 15d
    RELEASE GATE 4 (ros_buildfarm >= 4.2.0) :milestone, m4_gate, after m4_cache, 0d

    section Milestone 5 (Production Deployment)
    ros_buildfarm_config production distros :active, m5_config, after m4_gate, 30d
    Full End-to-End Production Active       :milestone, m5_active, after m5_config, 0d
```

* Comprehensive cross-repository tracking, Gantt milestone schedule, and issue links across all 5 stages are maintained in [`STAGE_PR_AND_ISSUE_MAP.md`](https://github.com/KmoM88/rep159-testing/blob/main/STAGE_PR_AND_ISSUE_MAP.md).

### Repository & Branch Matrix

| Repository | Branch / Track | Purpose |
|---|---|---|
| **`reps`** | [`feature/rep-159-binary-name-templating`](https://github.com/KmoM88/reps/tree/feature/rep-159-binary-name-templating) ([`openrobotics/reps#35`](https://github.com/openrobotics/reps/pull/35))<br>[`feature/rep-159-install-rule`](https://github.com/KmoM88/reps/tree/feature/rep-159-install-rule) (Stacked) | REP-159 specification updates: `binary_rule` regex engine, canonical lowercase variables, and optional `install_rule` directive |
| **`rosdistro`** | [`feature/rep159-binary-naming-regex`](https://github.com/rep159-testing/rosdistro/tree/feature/rep159-binary-naming-regex) ([`rep159-testing/rosdistro#1`](https://github.com/rep159-testing/rosdistro/pull/1))<br>[`feat/rep159-install-rule`](https://github.com/rep159-testing/rosdistro/tree/feat/rep159-install-rule) (Stacked PR-Ready) | Format 3 parser, `extends` DAG, `binary_rule` regex engine, and `install_rule` prefixes |
| **`rosdep`** | [`rep159`](https://github.com/rep159-testing/rosdep/tree/rep159) (Org Testbed)<br>[`feat/rep159-binary-lookup`](https://github.com/rep159-testing/rosdep/tree/feat/rep159-binary-lookup) (PR-Ready) | Delegates OS binary package name lookups to `rosdistro.get_binary_package_name()`. `rep159` includes testbed CI overrides; `feat/rep159-binary-lookup` is the clean, unencumbered branch targeting upstream `ros-infrastructure/rosdep:master` once Gate 1 (`rosdistro >= 1.2.0`) is released. |
| **`reprepro-updater`** | [`feat/package-prefix`](https://github.com/rep159-testing/reprepro-updater/tree/feat/package-prefix) | Selective APT suite promotion & cleanup via `--package-prefix` (targets upstream `refactor` directly) |
| **`ros_buildfarm`** | **Testbed:** [`feat/binary-naming-rule`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/binary-naming-rule), [`rep159`](https://github.com/rep159-testing/ros_buildfarm/tree/rep159)<br>**PR-Ready (off `master`):**<br>• [`feat/rep159-binary-naming`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/rep159-binary-naming) (Release jobs & naming)<br>• [`feat/rep159-workspace-walk`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/rep159-workspace-walk) (PR 3A: CI walk boundary)<br>• [`feat/rep159-underlays`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/rep159-underlays) (PR 3B: Dynamic underlays & pure-CMake env) | Core release job generation, workspace checkout boundaries, dynamic underlay injection, and pure-CMake environment fallbacks. PR-ready branches are completely free of Dockerfile pip hacks and target `ros-infrastructure/ros_buildfarm:master`. |
| **`rep159-rosdistro`** | [`feat/extendable-distro`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/extendable-distro) | Root `extendable` distribution file defining `binary_rule` and `install_rule` |
| **`ros_buildfarm_config`** | [`feat/extendable-distro`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/extendable-distro) | Release and sync build files with target repository definitions |
| **`upstream_a-release`** | [`debian/vendor-extendable/resolute/upstream_a`](https://github.com/rep159-testing/upstream_a-release/tree/debian/vendor-extendable/resolute/upstream_a) | Debian release track for `upstream_a` (`vendor-extendable-upstream-a`) |
| **`upstream_b-release`** | [`debian/vendor-extendable/resolute/upstream_b`](https://github.com/rep159-testing/upstream_b-release/tree/debian/vendor-extendable/resolute/upstream_b) | Debian release track for `upstream_b` (`vendor-extendable-upstream-b`) |
| **`upstream_c-release`** | [`debian/vendor-extendable/resolute/upstream_c`](https://github.com/rep159-testing/upstream_c-release/tree/debian/vendor-extendable/resolute/upstream_c) | Debian release track for `upstream_c` (`vendor-extendable-upstream-c`) |

### Executed Jobs & Configuration References

* **Source Release Pipeline**:
  - [`Esrc_uR__upstream_a__ubuntu_resolute__source`](https://build.test.ros2.org/job/Esrc_uR__upstream_a__ubuntu_resolute__source) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/extendable-distro/extendable/release-build.yaml)
  - [`Esrc_uR__upstream_b__ubuntu_resolute__source`](https://build.test.ros2.org/job/Esrc_uR__upstream_b__ubuntu_resolute__source) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/extendable-distro/extendable/release-build.yaml)
  - [`Esrc_uR__upstream_c__ubuntu_resolute__source`](https://build.test.ros2.org/job/Esrc_uR__upstream_c__ubuntu_resolute__source) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/extendable-distro/extendable/release-build.yaml)
* **Binary Packaging Pipeline**:
  - [`Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Ebin_uR64__upstream_a__ubuntu_resolute_amd64__binary) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/extendable-distro/extendable/release-build.yaml)
  - [`Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Ebin_uR64__upstream_b__ubuntu_resolute_amd64__binary) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/extendable-distro/extendable/release-build.yaml)
  - [`Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Ebin_uR64__upstream_c__ubuntu_resolute_amd64__binary) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/extendable-distro/extendable/release-build.yaml)
* **Repository Synchronization**:
  - [`Erel_sync-packages-to-testing_resolute_amd64`](https://build.test.ros2.org/job/Erel_sync-packages-to-testing_resolute_amd64) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/extendable-distro/extendable/release-build.yaml)

### Verified Invariants

* **Hermetic Binary Naming**: Built Debian packages match `vendor-extendable-upstream-{a,b,c}_0.1.0-1resolute_amd64.deb`.
* **Inter-Package Dependency Resolution**: `vendor-extendable-upstream-b` depends strictly on `vendor-extendable-upstream-a`, and `vendor-extendable-upstream-c` depends on `vendor-extendable-upstream-b`.
* **Repository Ingestion**: Packages are imported without naming collisions into `building` and synchronized to `testing`.

---

## Thematic Block 2: Advanced Topological Validations (Pure CMake Scope)

> [!NOTE]
> **Scope & Distribution Suite (`extendable*`)**: Validates pure CMake packages (`<build_type>cmake</build_type>`) across the **`extendable` distribution suite** (`extendable`, `extendablesrc`, `extendablebin`, `extendablechain`, `extendablechainedsrc`, `extendablechainedbin`, `extendablemixed`, `extendablediamond` — Jenkins job prefix **`E*`**). In this block, underlays are chained via buildfarm environment variable exports (`CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`, `PATH`) rather than relying on prefix `setup.sh` shell scripts, isolating pure graph and packaging algorithms from ROS shell complexities.

### Topology 1: Single-Tier Binary Import

#### Architectural Model

```mermaid
graph TD
    E1["extendable (Root APT Repo)<br/>vendor-extendable-upstream-*<br/>Prefix: /opt/ros/extendable"] -->|binary_import| EB1["extendablebin<br/>Workspace: downstream_bin_a (Source)<br/>APT Dependency: vendor-extendable-upstream-c"]
```

#### Behavior & Topological Invariants
Validates single-tier binary consumption where leaf packages build against parent distributions installed strictly from Debian repositories.
- `rosdep` maps ROS package dependency `upstream_c` to Debian package `vendor-extendable-upstream-c`.
- Buildfarm automatically derives parent result spaces and exports `CMAKE_PREFIX_PATH=/opt/ros/extendable`.

#### Repository & Branch Matrix
* **`ros_buildfarm_config`**: [`feat/stage3-chained-extensions`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/stage3-chained-extensions)
* **`rep159-rosdistro`**: [`feat/extendable-install-rule`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/extendable-install-rule)
* **`ros_buildfarm`**: [`feat/binary-naming-rule`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/binary-naming-rule) (Testbed) / [`feat/rep159-underlays`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/rep159-underlays) (PR-Ready)
* **`rosdistro`**: [`feat/rep159-install-rule`](https://github.com/rep159-testing/rosdistro/tree/feat/rep159-install-rule) (Stacked PR-Ready)
* **`rosdep`**: [`feat/rep159-binary-lookup`](https://github.com/rep159-testing/rosdep/tree/feat/rep159-binary-lookup) (PR-Ready)
* **Source Repositories**: `downstream_bin_a` (`main`)

#### Executed Jobs & Configuration References
* [`Eci__binary-import_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Eci__binary-import_ubuntu_resolute_amd64) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-chained-extensions/extendablebin/ci-nightly-release.yaml)

---

### Topology 2: Multi-Tier Source Rebuild ($A \to B \to C$)

#### Architectural Model

```mermaid
graph TD
    E2["extendable (Root Ancestor)"] -->|binary_import| EB2["extendablebin (Intermediate)"]
    EB2 -->|source_rebuild| EC2["extendablechain (Leaf Workspace)<br/>Clones and compiles all 5 source packages"]
```

#### Behavior & Topological Invariants
Validates multi-tier source rebuilds across parent boundary lines.
- `rosdistro` recursively walks the parent hierarchy (`extendablechain` $\to$ `extendablebin` $\to$ `extendable`).
- Colcon compiles all 5 packages in topological order within a single hermetic workspace without APT binary dependencies.

#### Repository & Branch Matrix
* **`ros_buildfarm_config`**: [`feat/stage3-chained-extensions`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/stage3-chained-extensions)
* **`rep159-rosdistro`**: [`feat/stage3-chained-extensions`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/stage3-chained-extensions)
* **`ros_buildfarm`**: [`feat/binary-naming-rule`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/binary-naming-rule)
* **Source Repositories**: `upstream_{a,b,c}` (`main`), `downstream_bin_a` (`main`), `downstream_chain_a` (`main`)

#### Executed Jobs & Configuration References
* [`Eci__source-rebuild_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Eci__source-rebuild_ubuntu_resolute_amd64) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-chained-extensions/extendablechain/ci-nightly-release.yaml)

---

### Topology 3: Pure Chained Binary Import ($A \xrightarrow{\text{bin}} B \xrightarrow{\text{bin}} C$)

#### Architectural Model

```mermaid
graph TD
    E3["extendable (Root APT Repo)<br/>vendor-extendable-upstream-*"] -->|binary_import| EB3["extendablebin (Intermediate APT Repo)<br/>ros-extendablebin-downstream-bin-a"]
    EB3 -->|binary_import| EC3["extendablechain (Leaf Workspace)<br/>Workspace: downstream_chain_a (Source)<br/>Underlays: /opt/ros/extendable:/opt/ros/extendablebin"]
```

#### Behavior & Topological Invariants
Validates multi-tier binary dependency chaining where each level is released as Debian packages into APT.
- Intermediate tier package `downstream_bin_a` compiles in chroot against `/opt/ros/extendable` and installs into `/opt/ros/extendablebin`.
- Grandchild workspace contains **only** leaf package `downstream_chain_a`.
- `rosdep` installs `ros-extendablebin-downstream-bin-a` and transitively `vendor-extendable-upstream-c`.
- Buildfarm injects cascading underlays: `ROS_BUILDFARM_PARENT_RESULT_SPACES=/opt/ros/extendable:/opt/ros/extendablebin`.
- Multiarch dynamic library search path (`LD_LIBRARY_PATH`) and `CMAKE_PREFIX_PATH` are automatically resolved for packages lacking `setup.sh`.

#### Repository & Branch Matrix
* **`ros_buildfarm_config`**: [`feat/stage3-binary-chained`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/stage3-binary-chained)
* **`rep159-rosdistro`**: [`feat/stage3-binary-chained`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/stage3-binary-chained)
* **`ros_buildfarm`**: [`feat/binary-naming-rule`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/binary-naming-rule)
* **Source Repositories**: `downstream_chain_a` (`main`), `downstream_bin_a` (`main`)
* **Release Repositories**: `downstream_bin_a-release` (`debian/extendablebin/resolute/downstream_bin_a`)

#### Executed Jobs & Configuration References
* **Intermediate Release Pipeline**:
  - [`Esrc_uR__downstream_bin_a__ubuntu_resolute__source`](https://build.test.ros2.org/job/Esrc_uR__downstream_bin_a__ubuntu_resolute__source) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-binary-chained/extendablebin/release-build.yaml)
  - [`Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-binary-chained/extendablebin/release-build.yaml)
  - [`Erel_sync-packages-to-testing_resolute_amd64`](https://build.test.ros2.org/job/Erel_sync-packages-to-testing_resolute_amd64) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-binary-chained/extendablebin/release-build.yaml)
* **Chained Binary CI Validation**:
  - [`Eci__chained-import_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Eci__chained-import_ubuntu_resolute_amd64) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-binary-chained/extendablechain/ci-nightly-release.yaml)

---

### Topology 4: Hybrid Mixed Extension (Binary Underlay + Source Overlay)

#### Architectural Model

```mermaid
graph TD
    E4["extendable (Root APT Repo)<br/>vendor-extendable-upstream-*"] -->|binary_import| EB4["extendablebin (Intermediate APT Repo)<br/>ros-extendablebin-downstream-bin-a"]
    EB4 -->|binary_import| EM4["extendablemixed (Workspace)<br/>Source: downstream_chain_a + upstream_c<br/>APT: ros-extendablebin-downstream-bin-a"]
```

#### Behavior & Topological Invariants
Validates developer workflows where pre-built binary dependencies are installed from APT while an ancestor package is checked out and rebuilt from source in the workspace.
- **ABI Immutability Rule**: `distribution.yaml` does not override `upstream_c` under `binary_import` (protecting ABI compatibility). The source override is declared strictly at CI job level (`repository_names: [downstream_chain_a, upstream_c]`).
- `rosdep --ignore-src` skips APT installation of `upstream_c` because it is present in the workspace source space.
- APT installs pre-built `ros-extendablebin-downstream-bin-a`.
- `downstream_chain_a` links against workspace source-built `upstream_c` and binary underlay `/opt/ros/extendablebin/lib/libdownstream_bin_a.so`.

> [!WARNING]
> **Architectural Governance & ABI Drift Consideration (Enforcing Binary Upstream)**:
> While this topology empirically proved that a local workspace can check out and compile an upstream ancestor from source (`upstream_c`) alongside an intermediate pre-built binary underlay (`downstream_bin_a`) using `rosdep --ignore-src` and CMake/Colcon overlay linking, **this may not be a desirable or recommended production behavior**:
> 1. **Risk of ABI Drift & Dual-Linking**: The intermediate binary package `downstream_bin_a.deb` was compiled and linked against the canonical binary release of `upstream_c.deb`. If the leaf workspace overrides `upstream_c` from source with modified struct layouts, signatures, or state, `downstream_bin_a.so` in the underlay remains linked against the original binary ABI while `downstream_chain_a` links against the new source version. This creates potential One Definition Rule (ODR) violations and subtle memory corruption bugs.
> 2. **Strict Binary Upstream Enforcement**: From an architectural and release-engineering standpoint, if an extension hierarchy declares `binary_import`, **everything above that boundary should strictly enforce binary resolution**. Even though compiling an upstream source in chains that begin with a `binary_import` is technically feasible at the workspace level, distribution governance should generally disallow mutating upstream dependencies across binary boundaries.
> 3. **Production Recommendation**: When an upstream ancestor requires modification or patching, distributions should establish a pure `source_rebuild` chain from that ancestor downwards, preserving hermetic end-to-end ABI consistency.

#### Repository & Branch Matrix
* **`ros_buildfarm_config`**: [`feat/stage3-mixed`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/stage3-mixed)
* **`rep159-rosdistro`**: [`feat/stage3-mixed`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/stage3-mixed)
* **`ros_buildfarm`**: [`feat/binary-naming-rule`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/binary-naming-rule)
* **Source Repositories**: `downstream_chain_a` (`main`), `upstream_c` (`main`)

#### Executed Jobs & Configuration References
* [`Eci__mixed-chain_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Eci__mixed-chain_ubuntu_resolute_amd64) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-mixed/extendablemixed/ci-nightly-release.yaml)

---

### Topology 5: Multi-Parent Diamond Extension (Convergent DAG)

#### Architectural Model

```mermaid
graph TD
    E5["extendable (Root Ancestor)"] -->|binary_import| EB5["extendablebin"]
    E5 -->|source_rebuild| ES5["extendablesrc"]
    EB5 -->|binary_import| ED5["extendablediamond (Multi-Parent Child)"]
    ES5 -->|source_rebuild| ED5
```

#### Behavior & Topological Invariants
Validates multi-parent inheritance where a child distribution declares multiple parents with different extension methods converging back to a shared root ancestor.
- **Multi-Parent Resolution**: `rosdistro` resolves `extends: [extendablebin (binary_import), extendablesrc (source_rebuild)]`.
- **Topological Underlay Deduplication**: `get_binary_import_underlays()` traverses both paths of the DAG, identifies the shared root ancestor, and deduplicates the result space path:
  `ROS_BUILDFARM_PARENT_RESULT_SPACES=/opt/ros/extendable:/opt/ros/extendablebin`
- APT installs pre-built `ros-extendablebin-downstream-bin-a`.
- Colcon compiles `downstream_src_a` and `downstream_chain_a` in the same workspace and passes 100% of unit test suites.

> [!NOTE]
> **Architectural Consideration: CI Scope & Pruning Unused Sources in Convergent DAGs**:
> In this diamond topology, the leaf distribution `extendablediamond` links its target package `downstream_chain_a` exclusively against the binary underlay `downstream_bin_a` from the left (`binary_import`) branch. However, because the right branch declared `source_rebuild`, `downstream_src_a` was also checked out, compiled, and tested in the CI container even though it is not consumed anywhere by `downstream_chain_a`.
> * **Governance & Default Behavior Consideration**: In production distribution maintenance, if a leaf distribution resolves its final runtime dependencies strictly from binary packages, building and testing unreferenced source packages from parallel `source_rebuild` branches may introduce unnecessary build overhead and compute cost. Future default behaviors or CI policies could consider transitive dependency pruning (e.g., pruning source checkout and build steps to only packages required by the distribution's released targets, using `--packages-up-to` or dependency-graph filtering) unless full-suite regression testing is explicitly desired.

#### Repository & Branch Matrix
* **`ros_buildfarm_config`**: [`feat/stage3-diamond`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/stage3-diamond)
* **`rep159-rosdistro`**: [`feat/stage3-diamond`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/stage3-diamond)
* **`ros_buildfarm`**: [`feat/binary-naming-rule`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/binary-naming-rule)
* **Source Repositories**: `downstream_chain_a` (`main`), `downstream_src_a` (`main`)

#### Executed Jobs & Configuration References
* [`Eci__diamond-chain_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Eci__diamond-chain_ubuntu_resolute_amd64) (Status: SUCCESS) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/stage3-diamond/extendablediamond/ci-nightly-release.yaml)

---

## Thematic Block 3: Composable Suite & Native `ros_workspace` Integration

> [!IMPORTANT]
> **Distribution Suite Shift (`extendable*` $\to$ `composable*`)**:
> - **Thematic Blocks 1 & 2 (`extendable` Suite, Jenkins Jobs `E*`)**: Evaluated core REP-159 algorithms (binary naming regex, install rules, DAG resolution, workspace checkout pruning) using pure CMake test packages without ROS shell environment files. Underlays were injected by buildfarm environment variable exports (`CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`).
> - **Thematic Block 3 (`composable` Suite, Jenkins Jobs `C*`)**: Advances to full **ROS 2 native environment sourcing** (`ros_workspace`, `/opt/ros/<distro>/setup.sh`, `.dsv` hooks) and automated Debian release generation via **`bloom`**, testing standard ROS 2 package lifecycles where child setups recursively source parent underlays.

> [!NOTE]
> **Execution Status Notice**: Because the public ROS 2 testfarm (`build.test.ros2.org`) is currently offline/unavailable, all release pipeline and CI runs for the `composable` distribution suite have been validated and confirmed 100% green on a local replica buildfarm cluster. Once the public testfarm is restored, these exact job configurations can be triggered directly.

### Architecture & Underlay Chaining Model

```mermaid
graph TD
    subgraph ComposableSuite [The composable Distribution Family]
        C["composable (Root Distro)<br/>Prefix: /opt/ros/composable<br/>binary_rule: vendor-composable-@PKG@<br/>Provides: ros_workspace, upstream_{a,b,c}"]
        
        U["upstream (Underlay Distro)<br/>Prefix: /opt/ros/upstream<br/>Provides: ament_cmake_core, ament_package"]
        
        U -.->|Environment Chaining<br/>AMENT_PREFIX_PATH / CMAKE_PREFIX_PATH| C
        
        CB["composablebin<br/>extends: composable (binary_import)<br/>Prefix: /opt/ros/composablebin"]
        CS["composablesrc<br/>extends: composable (source_rebuild)<br/>Prefix: /opt/ros/composablesrc"]
        
        C -->|binary_import| CB
        C -->|source_rebuild| CS
    end
```

### Feature Mechanics & Tooling Innovations

1. **Native ROS 2 Shell Environment (`ros_workspace`)**:
   - Transitions from artificial environment variable injection to native ROS 2 underlay environment sourcing.
   - Sourcing `/opt/ros/composable/setup.sh` evaluates `.dsv` environment hooks, sets `AMENT_PREFIX_PATH`, `CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`, and recursively incorporates `/opt/ros/upstream`.

2. **Dedicated Packaging Tooling Fork (`rep159-testing/bloom`)**:
   - Standard `bloom` hardcodes `Package: ros-@ROS_DISTRO@-@PKG@` and `CMAKE_INSTALL_PREFIX="/opt/ros/@ROS_DISTRO@"`.
   - The fork on branch `feat/rep159-rules-support`:
     - Queries `rosdistro.get_binary_package_name()` to format Debian control dependencies dynamically according to `binary_rule`.
     - Parameterizes `CMAKE_INSTALL_PREFIX` according to `install_rule`.
     - Generates multi-tier underlay sourcing logic inside `debian/rules`.

3. **Hermetic Release & CI Execution**:
   - `vendor-composable-ros-workspace` is packaged as an independent `.deb` archive installed into `/opt/ros/composable`.
   - In CI jobs (`Cci`), `ros_buildfarm` installs `vendor-composable-ros-workspace` via APT, detects `/opt/ros/composable/setup.sh`, and executes builds natively:
     ```bash
     . /opt/ros/composable/setup.sh && colcon build ...
     . /opt/ros/composable/setup.sh && colcon test ...
     ```

### Repository & Branch Matrix

| Repository | Branch / Track | Purpose |
|---|---|---|
| **`bloom`** | [`feat/rep159-rules-support`](https://github.com/rep159-testing/bloom/tree/feat/rep159-rules-support) | Packaging generator honoring `binary_rule` and `install_rule` (commit `45fb575`) |
| **`ros_workspace`** | [`feat/rep159-parent-chaining`](https://github.com/rep159-testing/ros_workspace/tree/feat/rep159-parent-chaining) | Reconciled underlay chaining configuration for `/opt/ros/composable` (commit `1805a69`) |
| **`ros_buildfarm`** | [`feat/rep159-binary-naming`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/rep159-binary-naming) | PR 3C release naming delegation, child release job isolation, and sync prefix (commit `9b02768`) |
| **`ros_workspace-release`** | [`debian/vendor-composable/resolute/ros_workspace`](https://github.com/rep159-testing/ros_workspace-release/tree/debian/vendor-composable/resolute/ros_workspace) | Release track and tag `debian/vendor-composable-ros-workspace_1.0.4-1_resolute` |
| **`upstream_{a,b,c}-release`** | [`debian/vendor-composable/resolute/upstream_{a,b,c}`](https://github.com/rep159-testing/upstream_a-release/tree/debian/vendor-composable/resolute/upstream_a) | Release tracks and tags `debian/vendor-composable-upstream-{a,b,c}_0.1.0-1_resolute` |
| **`downstream_bin_a-release`** | [`debian/vendor-composablebin/resolute/downstream_bin_a`](https://github.com/rep159-testing/downstream_bin_a-release/tree/debian/vendor-composablebin/resolute/downstream_bin_a) | Release track and tag `debian/vendor-composablebin-downstream-bin-a_0.2.0-1_resolute` |
| **`rep159-rosdistro`** | [`feat/composable-distro`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/composable-distro) | Distribution definitions for `composable` and `composablebin` |
| **`ros_buildfarm_config`** | [`feat/composable-distro`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/composable-distro) | Buildfarm release, sync, and CI configurations (`composable/`, `composablebin/`) |

### Executed Jobs & Configuration References

* **Workspace & Root Distro Release Pipelines (`composable`)**:
  - [`Csrc_uR__ros_workspace__ubuntu_resolute__source`](https://build.test.ros2.org/job/Csrc_uR__ros_workspace__ubuntu_resolute__source) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Cbin_uR64__ros_workspace__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Cbin_uR64__ros_workspace__ubuntu_resolute_amd64__binary) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Csrc_uR__upstream_a__ubuntu_resolute__source`](https://build.test.ros2.org/job/Csrc_uR__upstream_a__ubuntu_resolute__source) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Cbin_uR64__upstream_a__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Cbin_uR64__upstream_a__ubuntu_resolute_amd64__binary) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Csrc_uR__upstream_b__ubuntu_resolute__source`](https://build.test.ros2.org/job/Csrc_uR__upstream_b__ubuntu_resolute__source) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Cbin_uR64__upstream_b__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Cbin_uR64__upstream_b__ubuntu_resolute_amd64__binary) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Csrc_uR__upstream_c__ubuntu_resolute__source`](https://build.test.ros2.org/job/Csrc_uR__upstream_c__ubuntu_resolute__source) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Cbin_uR64__upstream_c__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Cbin_uR64__upstream_c__ubuntu_resolute_amd64__binary) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Crel_sync-packages-to-testing_resolute_amd64`](https://build.test.ros2.org/job/Crel_sync-packages-to-testing_resolute_amd64) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/release-build-local.yaml)
  - [`Cci__nightly-release_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Cci__nightly-release_ubuntu_resolute_amd64) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composable/ci-nightly-release-local.yaml)
* **Downstream Extension Pipelines (`composablebin` Overlay via `binary_import`)**:
  - [`Csrc_uR__downstream_bin_a__ubuntu_resolute__source`](https://build.test.ros2.org/job/Csrc_uR__downstream_bin_a__ubuntu_resolute__source) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composablebin/release-build-local.yaml)
  - [`Cbin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary`](https://build.test.ros2.org/job/Cbin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composablebin/release-build-local.yaml)
  - [`Cci__binary-import_ubuntu_resolute_amd64`](https://build.test.ros2.org/job/Cci__binary-import_ubuntu_resolute_amd64) (Status: Validated locally; pending remote testfarm) — [Job Config](https://github.com/rep159-testing/ros_buildfarm_config/blob/feat/composable-distro/composablebin/ci-nightly-release-local.yaml)


### Verified Invariants

* **Native Setup Sourcing**: Container verified presence of `/opt/ros/composable/setup.sh` and sourced it automatically prior to building and testing.
* **Underlay Chain Inheritance**: `upstream_a`, `upstream_b`, and `upstream_c` compiled with `colcon` and resolved build dependencies (`ament_cmake_core`) from the chained `/opt/ros/upstream` underlay without manual environment intervention.
* **Downstream Binary Overlay Chaining**: `downstream_bin_a` compiled and linked against `vendor-composable-upstream-c` installed via `binary_import` under prefix `/opt/ros/composable`, verifying seamless cross-distribution ABI and environment inheritance.
* **Hermetic Unit Test Execution**: 100% unit tests passed across all packages with CTest and GoogleTest XML reports archived.

---

## Stage 5: Distribution Cache Lifecycle & Bloom Packaging Validation

### Architectural Objectives & Topology

Stage 5 validates two essential operational pillars in hierarchical distributions under REP-159 without unnecessary multi-tier complexity:
1. **Cache Lifecycle & Hierarchy**: Validating how `rosdistro_build_cache` builds, publishes, isolates, invalidates, and refreshes distribution caches across parent-child boundaries.
2. **Automated Debian Packaging with Bloom**: Verifying that the REP-159 Bloom fork (`submodules/bloom`) generates complete, valid `debian/control` and `debian/rules` configurations directly from `distribution.yaml` metadata.

```mermaid
graph TD
    subgraph MinimalCacheSuite [Stage 5 Minimal Cache Validation Suite]
        CB["cachebase (Root Distro)<br/>Prefix: /opt/ros/cachebase<br/>binary_rule: vendor-cachebase-@PKG@<br/>Packages: upstream_a, upstream_b, upstream_c"]
        
        CC["cachechild (Overlay Distro)<br/>extends: cachebase (binary_import)<br/>Prefix: /opt/ros/cachechild<br/>binary_rule: vendor-cachechild-@PKG@<br/>Packages: downstream_bin_a"]

        CB -->|binary_import| CC
    end
```

### Key Technical Mechanisms

1. **REP-159 Enabled Cache Generator (`ros_buildfarm`)**:
   - Upstream `rosdistro_cache_task.Dockerfile.em` relies on Ubuntu Focal APT packages that lack ROSDistro Format 3 support (`extends`, `binary_rule`, `install_rule`).
   - Branch `feat/cache-job-rep159` injects the REP-159 `rosdistro` engine, allowing `rosdistro_build_cache` to parse extended distribution schemas inside the cache generation container.
   - Job assignment is directed to Docker-capable agents (`building_repository`), and cache archives (`<distro>-cache.yaml.gz`) are automatically published to the APT/Nginx mirror server via SSH.

2. **Parent Cache Inheritance & Boundary Isolation**:
   - When building `cachechild-cache.yaml.gz`, the generator fetches both `cachechild-cache.yaml.gz` and parent `cachebase-cache.yaml.gz`.
   - The engine validates cross-distribution dependencies, then performs clean boundary isolation (`- REMOVE upstream_a`, `- REMOVE upstream_b`, `- REMOVE upstream_c`) ensuring parent packages do not contaminate downstream overlay caches or alter parent ABI definitions.

3. **Cache Invalidation & Automated Reconfiguration**:
   - When package versions are bumped in `distribution.yaml` (e.g., `upstream_a` `0.1.0` $\to$ `0.1.1`), the cache job detects the change:
     ```text
     - updated manifest of package 'upstream_a' to version '0.1.1'
     ```
   - The Jenkins Groovy post-build publisher triggers downstream reconfigurations and rebuilds automatically.

4. **Automated Bloom Release Generation (`bloom`)**:
   - Using `git-bloom-generate rosdebian` on branch `feat/rep159-rules-support`:
     - **Binary Naming**: Queries `rosdistro.get_binary_package_name()` to generate Debian package names and inter-package dependencies matching `binary_rule`:
       ```text
       Package: vendor-cachechild-downstream-bin-a
       Depends: ${shlibs:Depends}, ${misc:Depends}, libyaml-0-2, vendor-cachebase-upstream-c, vendor-cachechild-ros-workspace
       ```
     - **Install Prefix & PKG_CONFIG_PATH**: Automatically parameterizes `CMAKE_INSTALL_PREFIX="/opt/ros/cachechild"` and `PKG_CONFIG_PATH=/opt/ros/cachechild/lib/pkgconfig:/opt/ros/cachebase/lib/pkgconfig`.
     - **Chained Underlay Sourcing**: Injects recursive sourcing loops into all `debian/rules` debhelper targets:
       ```make
       if [ -f "/opt/ros/cachebase/setup.sh" ]; then . "/opt/ros/cachebase/setup.sh"; fi && if [ -f "/opt/ros/cachechild/setup.sh" ]; then . "/opt/ros/cachechild/setup.sh"; fi
       ```

### Repository & Branch Matrix

| Repository | Branch / Track | Purpose |
|---|---|---|
| **`bloom`** | [`feat/rep159-rules-support`](https://github.com/rep159-testing/bloom/tree/feat/rep159-rules-support) | Bloom packaging generator with REP-159 rules and gpgsign fix |
| **`downstream_bin_a-release`** | [`debian/cachechild/resolute/downstream_bin_a`](https://github.com/rep159-testing/downstream_bin_a-release/tree/debian/cachechild/resolute/downstream_bin_a) | Debian packaging generated by Bloom (`vendor-cachechild-downstream-bin-a`) |
| **`ros_buildfarm`** | [`feat/cache-job-rep159`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/cache-job-rep159) | Cache job templates updated for REP-159 Docker task & agent assignment |
| **`rep159-rosdistro`** | [`feat/cache-lifecycle-test`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/cache-lifecycle-test) | Minimal 2-tier distribution definitions (`cachebase` and `cachechild`) |
| **`ros_buildfarm_config`** | [`feat/cache-lifecycle-test`](https://github.com/rep159-testing/ros_buildfarm_config/tree/feat/cache-lifecycle-test) | Buildfarm config definitions for `cachebase` and `cachechild` suites |

### Executed Jobs & Verification References

* **Distribution Cache Generation Pipelines**:
  - `cachebase_rosdistro-cache` (Status: Validated on Local Testfarm, Build #18 SUCCESS) — [Job Template](https://github.com/rep159-testing/ros_buildfarm/blob/feat/cache-job-rep159/ros_buildfarm/templates/misc/rosdistro_cache_job.xml.em)
  - `cachechild_rosdistro-cache` (Status: Validated on Local Testfarm, Build #18 SUCCESS) — [Job Template](https://github.com/rep159-testing/ros_buildfarm/blob/feat/cache-job-rep159/ros_buildfarm/templates/misc/rosdistro_cache_job.xml.em)

### Verified Invariants

* **Isolated Overlay Caching**: Child distributions cleanly isolate their own packages (`cachechild-cache.yaml.gz`) while successfully inheriting parent dependency resolution without contaminating upstream state.
* **Deterministic Cache Invalidation**: Version updates in `distribution.yaml` trigger selective manifest refreshes and automated Jenkins build pipelines without full cache wipes.
* **Automated Packaging Compliance**: Bloom generates 100% compliant Debian packaging files directly from ROSDistro metadata without manual patching, respecting custom binary naming, custom install prefixes, and multi-tier underlay chaining.


