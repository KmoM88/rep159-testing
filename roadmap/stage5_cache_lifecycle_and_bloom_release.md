# Stage 5: `extendable` & `extendablebin` (`E*`) — Distribution Cache Lifecycle & Automated Packaging

## 1. Executive Summary & Problem Statement

Stage 5 validates two core operational capabilities of `ros_buildfarm` and `bloom` directly on `https://build.test.ros2.org` within the **`extendable` $\to$ `extendablebin` (`E*`)** hierarchy:
1. **Distribution Cache Lifecycle (`extendable_rosdistro-cache` & `extendablebin_rosdistro-cache`)**:
   Verifies that `rosdistro_build_cache` loads parent caches from `extends[].index_url` (`46a7580`), validates cross-distribution dependencies, strips inherited parent packages (`- REMOVE`) before writing `<child>-cache.yaml.gz`, publishes the cache over SSH, and runs Groovy post-build reconfigure checks.
2. **Automated Packaging Verification with Bloom (`git-bloom-generate rosdebian`)**:
   Verifies that `submodules/bloom` (`feat/rep159-rules-support` @ `7af7034`) generates `debian/control` and `debian/rules` honoring `binary_rule`, `install_rule`, and `ParentPrefixes`.

---

## 2. Design Decisions & Technical Rationale

| Decision | Mechanism | Verified Invariant on `build.test.ros2.org` |
|---|---|---|
| **1. Unified `extendable` $\to$ `extendablebin` Hierarchy** | `extendable` hosts 6 root packages (`ament_package`, `ament_cmake_core`, `ros_workspace`, `upstream_{a,b,c}`); `extendablebin` extends `extendable` (`binary_import`) with child `ros_workspace` + `downstream_bin_a`. | Zero namespace collision with `cargotest` (`C*`) or `jrivero` (`U*`/`S*`/`B*`). |
| **2. Cache Boundary Isolation (`- REMOVE`)** | `rosdistro_build_cache` loads `extendable-cache.yaml.gz`, resolves dependencies, and strips `ament_cmake_core`, `ament_package`, `upstream_{a,b,c}` before saving `extendablebin-cache.yaml.gz`. | Keeps child cache archives compact and prevents child distributions from mutating parent package manifests. |
| **3. GPG-Signed Tag Compatibility in Bloom** | `bloom/generators/debian/generator.py` (`d6fdf9e`) passes `-m "<tag_name>"` to `git tag -f`. | `git-bloom-generate` succeeds cleanly in environments with `tag.gpgSign=true`. |

---

## 3. Empirical Validation on `https://build.test.ros2.org`

### 3.1 Cache Generation & SSH Publishing (`extendable*_rosdistro-cache`)

| Job on `build.test.ros2.org` | Build & Console | Status | Verified Console Output & Artifact |
|---|---|:---:|---|
| `extendable_rosdistro-cache` | [#139](https://build.test.ros2.org/job/extendable_rosdistro-cache/139/) ([Log](https://build.test.ros2.org/job/extendable_rosdistro-cache/139/console)) | **SUCCESS** | Loaded all 6 manifests (`ament_package`, `ament_cmake_core`, `ros_workspace`, `upstream_{a,b,c}`), wrote `extendable-cache.yaml.gz`, and transferred 1 file via SSH (`rosdistro_cache`). |
| `extendablebin_rosdistro-cache` | [#138](https://build.test.ros2.org/job/extendablebin_rosdistro-cache/138/) ([Log](https://build.test.ros2.org/job/extendablebin_rosdistro-cache/138/console)) | **SUCCESS** | Loaded parent `extendable-cache.yaml.gz`, stripped `- REMOVE ament_cmake_core, ament_package, upstream_a, upstream_b, upstream_c`, kept `downstream_bin_a` + `ros_workspace`, and transferred `extendablebin-cache.yaml.gz` via SSH. |

### 3.2 Automated Bloom Debian Generation & Binary Build (`downstream_bin_a-release`)

- Generated branch [`debian/vendor-extendablebin/resolute/downstream_bin_a`](https://github.com/rep159-testing/downstream_bin_a-release/tree/debian/vendor-extendablebin/resolute/downstream_bin_a) (`9f8ba47`) and tag `debian/vendor-extendablebin-downstream-bin-a_0.2.0-1_resolute`:
  - `debian/control`: `Package: vendor-extendablebin-downstream-bin-a`, `Depends: ... vendor-extendable-upstream-c, vendor-extendablebin-ros-workspace`
  - `debian/rules`: `CMAKE_INSTALL_PREFIX="/opt/ros/extendablebin"`, `CMAKE_PREFIX_PATH="/opt/ros/extendablebin;/opt/ros/extendable"`, and parent `setup.sh` sourcing loop.
- Built and synced on `https://build.test.ros2.org`:
  - [`Esrc_uR__extbin_downstream_bin_a__ubuntu_resolute__source #1`](https://build.test.ros2.org/job/Esrc_uR__extbin_downstream_bin_a__ubuntu_resolute__source/1/) — **SUCCESS**
  - [`Ebin_uR64__extbin_downstream_bin_a__ubuntu_resolute_amd64__binary #2`](https://build.test.ros2.org/job/Ebin_uR64__extbin_downstream_bin_a__ubuntu_resolute_amd64__binary/2/) — **SUCCESS**
  - [`Erel_extbin_sync-packages-to-testing_resolute_amd64 #3`](https://build.test.ros2.org/job/Erel_extbin_sync-packages-to-testing_resolute_amd64/3/) — **SUCCESS**
