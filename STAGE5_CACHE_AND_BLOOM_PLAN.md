# Stage 5 Plan: Distribution Cache Lifecycle & Automated Bloom Packaging

Architecture, sequence flows, branch matrix, and validation evidence for **Stage 5** of the REP-159 testing campaign (`cachebase` $\to$ `cachechild`).

---

## 1. Cache Generation & Parent Inheritance Flow (`rosdistro_build_cache`)

```mermaid
sequenceDiagram
    autonumber
    participant Jenkins as Jenkins (<distro>_rosdistro-cache)
    participant Docker as Container (rosdistro_cache_task)
    participant Script as rosdistro_build_cache (rosdistro)
    participant Mirror as APT / Cache Server
    participant Reconfig as Jenkins (<distro>_reconfigure-jobs)

    Jenkins->>Docker: Run rosdistro_build_cache <index_url> cachechild
    Docker->>Script: Fetch cachechild/distribution.yaml & parent cachebase-cache.yaml.gz (46a7580)
    Script->>Script: Validate cross-distro dependencies & strip parent pkgs (- REMOVE upstream_{a,b,c})
    Script-->>Jenkins: Emit cachechild-cache.yaml.gz & manifest diff summary
    Jenkins->>Mirror: Publish cachechild-cache.yaml.gz over SSH
    Jenkins->>Reconfig: Groovy post-build regex triggers reconfigure on bumped package versions
```

---

## 2. Minimal 2-Tier Cache Hierarchy (`cachebase` $\to$ `cachechild`)

```mermaid
graph LR
    CB["cachebase (Root Distro)<br/>Prefix: /opt/ros/cachebase<br/>binary_rule: vendor-{distro}-{package}<br/>Packages: upstream_{a,b,c}"] -->|binary_import<br/>extends[].index_url| CC["cachechild (Overlay Distro)<br/>Prefix: /opt/ros/cachechild<br/>binary_rule: vendor-{distro}-{package}<br/>Packages: downstream_bin_a"]
```

| Property | `cachebase` (Root) | `cachechild` (Overlay) |
|---|---|---|
| **`extends`** | *(None)* | `[{distro_name: cachebase, extension_method: binary_import}]` |
| **`install_rule`** | `/opt/ros/{distro}` | `/opt/ros/{distro}` |
| **`binary_rule`** | `{search: '^', replace: 'vendor-{distro}-'}` | `{search: '^', replace: 'vendor-{distro}-'}` |
| **Own Packages in `<distro>-cache.yaml.gz`** | `upstream_a`, `upstream_b`, `upstream_c` | `downstream_bin_a` *(parent packages stripped via `- REMOVE`)* |
| **In-Memory `get_cached_distribution()`** | 3 packages | 4 packages (`downstream_bin_a` + merged parent `upstream_{a,b,c}`) |

---

## 3. Repository & Branch Matrix

| Submodule | Clean PR / Stage 5 Branch (`@ SHA`) | Key Commits & Role |
|---|---|---|
| **`rosdistro`** | [`feat/rep159-install-rule`](https://github.com/rep159-testing/rosdistro/tree/feat/rep159-install-rule) (`a8f5543`) | Includes `jrivero`'s `46a7580` (*"Load parent caches from extends[].index_url and fail if one cannot load"*) + `binary_rule` & `install_rule`. |
| **`bloom`** | [`feat/rep159-rules-support`](https://github.com/rep159-testing/bloom/tree/feat/rep159-rules-support) (`7af7034`) | Stacked on `jrivero`'s `origin/rep159` (`0189046`..`2877687`) + `binary_rule`, `install_rule`, and `d6fdf9e` (`git tag -f -m` GPG sign fix). |
| **`downstream_bin_a-release`** | [`debian/cachechild/resolute/downstream_bin_a`](https://github.com/rep159-testing/downstream_bin_a-release/tree/debian/cachechild/resolute/downstream_bin_a) (`2d645df`) | Debian packaging generated automatically via `git-bloom-generate rosdebian` (`Package: vendor-cachechild-downstream-bin-a`). |
| **`ros_buildfarm`** | [`feat/cache-job-rep159`](https://github.com/rep159-testing/ros_buildfarm/tree/feat/cache-job-rep159) (`6f62d7b`) | Testbed cache job template override (replaced upstream by **Release Gate 1** `python3-rosdistro-modules >= 1.2.0` in `ros_bootstrap` APT). |
| **`rep159-rosdistro` & `ros_buildfarm_config`** | [`feat/cache-lifecycle-test`](https://github.com/rep159-testing/rep159-rosdistro/tree/feat/cache-lifecycle-test) | `cachebase` and `cachechild` distribution and buildfarm config definitions. |

---

## 4. Verification Summary

| Test Case | Job / Tool | Build / Artifact | Status | Verified Output |
|---|---|---|:---:|---|
| **1. Root Cache Generation & Version Bump** | `cachebase_rosdistro-cache` | Build #18 | **SUCCESS** | Built `cachebase-cache.yaml.gz`; detected `0.1.0` $\to$ `0.1.1` bump (`- updated manifest of package 'upstream_a' to version '0.1.1'`). |
| **2. Child Cache Parent Merge & Boundary Strip** | `cachechild_rosdistro-cache` | Build #18 | **SUCCESS** | Loaded `cachebase-cache.yaml.gz`, resolved parent dependencies, stripped `- REMOVE upstream_{a,b,c}`, and published `cachechild-cache.yaml.gz`. |
| **3. Automated Bloom Debian Generation** | `git-bloom-generate rosdebian` | [`debian/cachechild/resolute/downstream_bin_a`](https://github.com/rep159-testing/downstream_bin_a-release/tree/debian/cachechild/resolute/downstream_bin_a) | **SUCCESS** | Generated `Package: vendor-cachechild-downstream-bin-a`, `Depends: ... vendor-cachebase-upstream-c, vendor-cachechild-ros-workspace`, `CMAKE_INSTALL_PREFIX="/opt/ros/cachechild"`, and chained `ParentPrefixes` in `debian/rules`. |
