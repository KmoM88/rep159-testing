# Stage 5: Distribution Cache Lifecycle & Automated Packaging

## 1. Executive Summary & Problem Statement

Two vital operational capabilities of `ros_buildfarm` required systematic exploration and verification:
1. **Distribution Cache Lifecycle in Hierarchical Distributions**:
   In standard buildfarms, `rosdistro_build_cache` builds compressed cache files (`<distro>-cache.yaml.gz`) published over HTTP. However, upstream task containers (`rosdistro_cache_task.Dockerfile.em`) lacked support for Format 3 schemas (`extends:`, `binary_rule`, `install_rule`). Crucially, the operational mechanics of how child overlays inherit parent caches, strip parent packages, and trigger automated downstream reconfigurations upon version bumps remained unverified.
2. **Automated Packaging Verification with Bloom**:
   Verifying that the REP-159 enabled `bloom` fork (`submodules/bloom` on `feat/rep159-rules-support`) can autonomously generate production-grade Debian packaging (`debian/control`, `debian/rules`) directly from distribution metadata without manual patching.

Stage 5 validates both capabilities end-to-end on a dedicated minimal 2-tier distribution hierarchy (`cachebase` $\to$ `cachechild`).

---

## 2. Design Decisions & Technical Rationale

### Decision 1: Minimal 2-Tier Topology (`cachebase` $\to$ `cachechild`)
* **Context**: Rather than testing cache mechanics on complex multi-tier diamond topologies, a clean, minimal 2-tier hierarchy was established:
  - `cachebase` (Root Distro): Hosts `upstream_a`, `upstream_b`, `upstream_c` under prefix `/opt/ros/cachebase` with `binary_rule: vendor-cachebase-@PKG@`.
  - `cachechild` (Overlay Distro): `extends: cachebase (binary_import)`, hosts `downstream_bin_a` under prefix `/opt/ros/cachechild` with `binary_rule: vendor-cachechild-@PKG@`.
* **Rationale**: Eliminates extraneous dependency noise, isolating cache inheritance, boundary de-merging, and invalidation mechanics.

### Decision 2: Cache Boundary Isolation (`- REMOVE`)
* **Discovery & Invariant**: When building an overlay cache, `rosdistro_build_cache` queries the parent cache (`cachebase-cache.yaml.gz`), verifies cross-distribution dependencies, and then strips parent entries (`- REMOVE upstream_{a,b,c}`) before writing `<distro>-cache.yaml.gz`.
* **Rationale**: Keeps downstream cache archives compact and guarantees that downstream distributions cannot accidentally mutate or shadow upstream package metadata.

### Decision 3: GPG-Signed Tag Compatibility in Bloom
* **Problem**: In developer environments configured with `tag.gpgSign=true`, invoking `git tag -f <tag>` without a message flag (`-m`) causes git to abort (`fatal: no tag message?`).
* **Adopted Solution**: Updated `bloom/generators/debian/generator.py` (line 869) to explicitly supply `-m "<tag_name>"`.

---

## 3. Implementation Breakdown: Core Code vs. Required Fixes vs. Pre-Release Overrides

### Core Feature Implementation & Required Fixes (To Be Merged Upstream)

1. **`ros-infrastructure/rosdistro` (`rep159` + `feature/rep159-binary-naming-regex` + `feature/rep159-install-rule`)**:
   - `DistributionCache` & `rosdistro_build_cache`: Serializes `extends`, `binary_rule`, and `install_rule` metadata, loads parent caches across distribution boundaries, and strips inherited parent packages (`- REMOVE <pkg>`) from child cache archives.

2. **`ros-infrastructure/bloom` (`feat/rep159-rules-support`, Commit `d6fdf9e`)**:
   - `bloom/generators/debian/generator.py` (line 869): Supplies `-m "<tag_name>"` to `git tag -f` so `git-bloom-generate` succeeds in environments with `tag.gpgSign=true` (zero dependency on `rosdistro`; ready in **Wave 0**).

3. **`ros-infrastructure/ros_buildfarm` (`setup.py` & `stdeb.cfg` Dependency Pinning — Wave 3)**:
   - Bumps `rosdistro >= 1.2.0` (`setup.py`) and `python3-rosdistro-modules (>= 1.2.0)` (`stdeb.cfg`).
   - Because `rosdistro/stdeb.cfg` builds `Suite3: focal jammy noble resolute bookworm trixie`, publishing **Gate 1 (`rosdistro >= 1.2.0`)** to `ros_bootstrap` APT automatically provides Format-3-capable `python3-rosdistro` inside `rosdistro_cache_task.Dockerfile.em` (`FROM ubuntu:focal`) with **zero** Dockerfile `pip` overrides. *(Note: If OSRF removes `focal` from `ros_bootstrap` before Gate 1, updating `rosdistro_cache_task.Dockerfile.em` and `release_check_sync_criteria_task.Dockerfile.em` from `ubuntu:focal` to `ubuntu:noble`/`jammy` becomes a required upstream change).*

### Temporary Pre-Release Overrides & Local Workarounds (Do NOT Upstream)

1. **Cache Task Tarball `pip3 install` & Agent Label Override (`feat/cache-job-rep159`, commits `8c1f978`, `6f62d7b`)**:
   - `rosdistro_cache_task.Dockerfile.em`: Injected `pip3 install https://github.com/rep159-testing/rosdistro/archive/refs/heads/feature/rep159-install-rule.tar.gz` only because Gate 1 was not yet in `ros_bootstrap` APT.
   - `rosdistro_cache_job.xml.em`: Changed `<assignedNode>built-in || master</assignedNode>` to `building_repository` only because the local Jenkins master container lacked a Docker CLI client.
2. **Reprepro `focal` Suite Export on Local Mirror**:
   - The cache task container uses base image `ubuntu:focal`. Adding `Codename: focal` and running `reprepro export focal` on the local mirror (`192.168.30.202:8088`) allowed container APT updates to pass cleanly.
3. **Jenkins Groovy Script Approvals & SSH Target**:
   - Approved the Groovy post-build regex scanner signature via `ScriptApproval` and mapped SSH publisher `rosdistro_cache` to `/var/repos/rep159-rosdistro/`.

---

## 4. Empirical Validation & Test Evidence

### Cache Generation & Propagation in Jenkins

* **Root Distro Cache (`cachebase_rosdistro-cache`)**:
  - Build #18 (**SUCCESS**): Built cache for `cachebase`, loaded package manifests for `upstream_{a,b,c}`, serialized `cachebase-cache.yaml.gz`, and transferred via SSH to the web mirror. Verified HTTP `200 OK`.
* **Overlay Distro Cache (`cachechild_rosdistro-cache`)**:
  - Build #18 (**SUCCESS**): Verified child cache execution log:
    ```text
    DEBUG:rosdistro:Load index from "http://192.168.30.202:8088/rep159-rosdistro/index-v4.yaml"
    Build cache for "cachechild"
    - trying to fetch cache
    DEBUG:rosdistro:Load cache from "http://192.168.30.202:8088/rep159-rosdistro/cachechild-cache.yaml.gz"
    DEBUG:rosdistro:Load cache from "http://192.168.30.202:8088/rep159-rosdistro/cachebase-cache.yaml.gz"
    - update cache
    DEBUG:rosdistro:Load file from "http://192.168.30.202:8088/rep159-rosdistro/cachechild/distribution.yaml"
    - removing invalid release package cache entries.
    - REMOVE upstream_a
    - REMOVE upstream_b
    - REMOVE upstream_c
    - fetch missing release manifests
      - fetch "downstream_bin_a"
    - write compressed cache file "cachechild-cache.yaml.gz"
    ```
  - Published `cachechild-cache.yaml.gz` via SSH to mirror. Verified HTTP `200 OK`.

### Cache Invalidation Test
* Bumped version of `upstream_a` in `cachebase/distribution.yaml` from `0.1.0` to `0.1.1` and pushed release tag.
* Ran `cachebase_rosdistro-cache`:
  - Build log confirmed: `- updated manifest of package 'upstream_a' to version '0.1.1'`.
  - Decompressed cache verified that `upstream_a` version updated to `0.1.1`.
  - Jenkins Groovy post-build regex scanner detected the change and triggered reconfigure tasks.

### Automated Bloom Release Packaging Validation
* Executed `git-bloom-generate -y -d rosdebian cachechild --os-name ubuntu --distros resolute -p release/extendablebin` in `submodules/downstream_bin_a-release`.
* **Validation of Generated `debian/control`**:
  ```debian
  Package: vendor-cachechild-downstream-bin-a
  Architecture: any
  Depends: ${shlibs:Depends}, ${misc:Depends}, libyaml-0-2, vendor-cachebase-upstream-c, vendor-cachechild-ros-workspace
  ```
  *(Correctly evaluated `binary_rule` for both the package and its inter-distribution parent dependency).*
* **Validation of Generated `debian/rules`**:
  ```make
  export PKG_CONFIG_PATH=/opt/ros/cachechild/lib/pkgconfig:/opt/ros/cachebase/lib/pkgconfig
  ...
  override_dh_auto_configure:
  	if [ -f "/opt/ros/cachebase/setup.sh" ]; then . "/opt/ros/cachebase/setup.sh"; fi && if [ -f "/opt/ros/cachechild/setup.sh" ]; then . "/opt/ros/cachechild/setup.sh"; fi && \
  	dh_auto_configure -- \
  		-DCMAKE_INSTALL_PREFIX="/opt/ros/cachechild" \
  		-DCMAKE_PREFIX_PATH="/opt/ros/cachechild;/opt/ros/cachebase" \
  		$(BUILD_TESTING_ARG)
  ```
* Pushed release branch `debian/cachechild/resolute/downstream_bin_a` and tag `debian/vendor-cachechild-downstream-bin-a_0.2.0-0_resolute` to GitHub `origin`.

---

## 5. Release-Gated Upstream PR & Release Sequence

1. **Wave 0 — `ros-infrastructure/bloom` (Zero Release Prerequisite)**:
   - *Title*: `fix(debian): pass tag message in git tag -f to support tag.gpgSign=true`
   - *Source Commit*: `d6fdf9e` on `feat/rep159-rules-support` $\to$ `master`.
2. **Wave 3 — `ros-infrastructure/ros_buildfarm` (Blocked Until Gate 1 `rosdistro >= 1.2.0` in `ros_bootstrap` APT)**:
   - *Mechanism*: Bump `rosdistro >= 1.2.0` in `setup.py` and `python3-rosdistro-modules (>= 1.2.0)` in `stdeb.cfg` (folded into Wave 3 `ros_buildfarm` release PRs), dropping the temporary `rosdistro_cache_task.Dockerfile.em` tarball `pip` override and `rosdistro_cache_job.xml.em` `assignedNode` override from `feat/cache-job-rep159`.
   - *Contingency Fix*: If `focal` is dropped from `ros_bootstrap` APT builds prior to Gate 1, include a template base-image bump (`ubuntu:focal` $\to$ `ubuntu:noble`) in `rosdistro_cache_task.Dockerfile.em` and `release_check_sync_criteria_task.Dockerfile.em`.
