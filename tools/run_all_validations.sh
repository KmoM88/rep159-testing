#!/usr/bin/env bash
# Runs the full suite of offline local validation checks for REP-159.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VERBOSE=false
SELECTED_SUITE=all

show_help() {
    cat << 'EOF'
Usage: ./tools/run_all_validations.sh [OPTIONS]

Options:
  -v, --verbose      Run tests in verbose mode (shows detailed pytest outputs)
  -s, --suite <1-7>  Run only a specific validation suite:
                       1: Rosdistro Format 3 & ABI Guardrails
                       2: Rosdep Binary Naming & Extension Resolution
                       3: Ros_Buildfarm Boundary Walk & Underlays
                       4: Cache Architecture & Dynamic Merging
                       5: Rep159-Rosdistro Workspace Resolution
                       6: Binary Package Renaming Engine (Regex)
                       7: Custom Installation Prefixes & Underlays (Regex)
  -h, --help         Show this help message and exit

Examples:
  ./tools/run_all_validations.sh
  ./tools/run_all_validations.sh --verbose
  ./tools/run_all_validations.sh --suite 6 --verbose
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--suite)
            SELECTED_SUITE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Ensure environment is ready
source "$REPO_ROOT/tools/setup_env.sh" > /dev/null

echo "======================================================================"
echo "          STARTING FULL LOCAL VALIDATION SUITE (REP-159)              "
echo "======================================================================"
echo " Mode: Verbose=$VERBOSE | Suite=$SELECTED_SUITE"
echo ""

FAILURES=0
V_ARG=""
if [ "$VERBOSE" = true ]; then
    V_ARG="-v"
fi

run_test() {
    local suite_num="$1"
    local title="$2"
    local cmd="$3"

    if [ "$SELECTED_SUITE" != "all" ] && [ "$SELECTED_SUITE" != "$suite_num" ]; then
        return 0
    fi

    echo ">>> Running: Suite $suite_num - $title..."
    if eval "$cmd"; then
        echo ">>> [PASS]: Suite $suite_num - $title"
    else
        echo ">>> [FAIL]: Suite $suite_num - $title"
        FAILURES=$((FAILURES + 1))
    fi
    echo "----------------------------------------------------------------------"
}

run_test 1 "Rosdistro Format 3 & ABI Guardrails" \
  "$REPO_ROOT/.venv/bin/python $REPO_ROOT/tools/validate_rosdistro.py $V_ARG"

run_test 2 "Rosdep Binary Naming & Extension Resolution" \
  "$REPO_ROOT/.venv/bin/python $REPO_ROOT/tools/validate_rosdep.py $V_ARG"

run_test 3 "Ros_Buildfarm Boundary Walk & Underlays" \
  "$REPO_ROOT/.venv/bin/python $REPO_ROOT/tools/validate_ros_buildfarm.py $V_ARG"

run_test 4 "Cache Architecture & Dynamic Merging" \
  "$REPO_ROOT/.venv/bin/python $REPO_ROOT/tools/validate_cache_lifecycle.py $V_ARG"

run_test 5 "Rep159-Rosdistro Workspace Resolution" \
  "$REPO_ROOT/.venv/bin/python $REPO_ROOT/submodules/rep159-rosdistro/tools/check_workspaces.py file://$REPO_ROOT/submodules/rep159-rosdistro/index-v4.yaml"

run_test 6 "Binary Package Renaming Engine (Regex)" \
  "$REPO_ROOT/.venv/bin/python $REPO_ROOT/tools/validate_binary_naming.py"

run_test 7 "Custom Installation Prefixes & Underlays (Regex)" \
  "$REPO_ROOT/.venv/bin/python $REPO_ROOT/tools/validate_install_prefixes.py"

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "======================================================================"
    echo "     ALL VALIDATION SUITES PASSED! (0 FAILURES)                       "
    echo "======================================================================"
    exit 0
else
    echo "======================================================================"
    echo "     VALIDATION FAILED: $FAILURES test suite(s) failed                "
    echo "======================================================================"
    exit 1
fi
