#!/usr/bin/env bash
# Sets up the local Python virtual environment and exports the required PYTHONPATH.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -d "$REPO_ROOT/.venv" ]; then
    echo "Creating Python virtual environment at $REPO_ROOT/.venv..."
    python3 -m venv "$REPO_ROOT/.venv"
fi

echo "Activating virtual environment..."
source "$REPO_ROOT/.venv/bin/activate"

echo "Ensuring required dependencies are installed..."
pip install -q --upgrade pip
pip install -q PyYAML catkin_pkg "empy==3.3.4" pytest flake8 rospkg vcstool jenkinsapi

# Install local submodules in editable mode (using current branch, avoiding PyPI)
echo "Ensuring local submodules are installed in editable mode from current branch..."
pip install -q --no-build-isolation --no-deps \
    -e "$REPO_ROOT/submodules/rosdistro" \
    -e "$REPO_ROOT/submodules/rosdep" \
    -e "$REPO_ROOT/submodules/ros_buildfarm" \
    -e "$REPO_ROOT/submodules/ament_package"

# Export PYTHONPATH pointing to the rep159 forks as an extra layer
export PYTHONPATH="$REPO_ROOT/submodules/ros_buildfarm:$REPO_ROOT/submodules/rosdistro/src:$REPO_ROOT/submodules/rosdep/src:${PYTHONPATH:-}"

echo "Environment ready!"
echo "PYTHONPATH=$PYTHONPATH"
