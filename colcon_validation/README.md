# REP-159 Distribution Extension Validation (`vcstool` + `colcon`)

Standalone workspace layout and instructions to verify **[REP-159](https://github.com/openrobotics/reps/pull/32)** (*rosdistro extension mechanism*) locally using `vcstool`, `rosdep`, `ros_buildfarm`, and `colcon` against the [`rep159-testing`](https://github.com/rep159-testing) repositories.

---

## 1. Repository Layout

```text
.
├── README.md
├── tooling.repos                        # vcstool manifest for REP-159 tooling & config repos
├── tooling_ws/
│   └── src/                             # Target directory for REP-159 tooling checkout
└── single_parent_source/
    ├── README.md                        # Instructions for single-parent all-source (source_rebuild)
    ├── distribution.repos               # vcstool manifest for extendablelyricalsrc source repos
    └── ws/
        └── src/                         # Target colcon source space for the distribution
```

---

## 2. Prerequisites (Ubuntu 24.04 Noble / 26.04 Resolute)

Install basic system build tools and Python virtual environment support:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git pkg-config python3 python3-pip python3-venv
```

---

## 3. One-Time REP-159 Tooling Setup

From the root of this repository, create a Python virtual environment (with `--system-site-packages` so `apt` Python packages installed later by `rosdep` are visible to CMake and `colcon test`), download the REP-159 tooling repositories from `rep159-testing` via `vcstool`, and install them:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

pip install --upgrade pip setuptools wheel "empy<4" vcstool colcon-common-extensions

vcs import tooling_ws/src < tooling.repos

pip install \
  tooling_ws/src/rosdistro \
  tooling_ws/src/rosdep \
  tooling_ws/src/bloom \
  tooling_ws/src/ros_buildfarm \
  tooling_ws/src/rosdistro-reviewer
```

Point `ROSDISTRO_INDEX_URL` to the `rep159-testing/rep159-rosdistro` index on GitHub:

```bash
export ROSDISTRO_INDEX_URL="https://raw.githubusercontent.com/rep159-testing/rep159-rosdistro/feat/extendable-gazebo/index-v4.yaml"
```

### Tooling & Configuration Branches Included in `tooling.repos`

| Repository | Branch | Role |
|---|---|---|
| `rep159-testing/rosdistro` | `feat/rep159-workspace-package` | Format v3 `extends`, `binary_rule`, `install_rule`, `workspace_package`, Index v4 `distribution_eol_date` |
| `rep159-testing/bloom` | `feat/rep159-workspace-package` | `ParentPrefixes`, `binary_rule`, `install_rule`, `workspace_package` Debian generation |
| `rep159-testing/rosdep` | `feat/rep159-binary-lookup` | Delegates binary package naming and extended distro lookup to `rosdistro` |
| `rep159-testing/ros_buildfarm` | `feat/rep159-core` | `ReleaseAndSourceDependencyWalker`, `create_workspace.py`, underlay chaining, `workspace_package` |
| `rep159-testing/rosdistro-reviewer` | `rep159` | Index v4 `distribution_eol_date` validation |
| `rep159-testing/reprepro-updater` | `rep159` | `--package-prefix` APT sync filtering |
| `rep159-testing/ros_workspace` | `rep159` | Ament workspace underlay chaining (`ROS_WORKSPACE_PARENT_PREFIX_PATH`) |
| `rep159-testing/ros_workspace_shell` | `rep159` | Plain-CMake prefix setup scripts (`setup.sh` / `local_setup.sh`) without Ament |
| `rep159-testing/rep159-rosdistro` | `feat/extendable-gazebo` | REP-159 `index-v4.yaml`, distribution manifests, and caches |
| `rep159-testing/ros_buildfarm_config` | `feat/extendable-gazebo` | Buildfarm CI and release configurations |

---

## 4. Validation Scenarios

| Scenario | Topology | Child Distribution | Parent(s) | Instructions |
|---|---|---|---|---|
| **Single-Parent All-Source** | `source_rebuild` | `extendablelyricalsrc` | `extendablejetty` | [`single_parent_source/README.md`](single_parent_source/README.md) |
