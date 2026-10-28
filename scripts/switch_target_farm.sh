#!/bin/bash
# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0
#
# Script to switch target buildfarm environment between 'local' and 'remote' (build.test.ros2.org)
# Automatically loads credentials from .env if present.

TARGET="${1:-local}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Auto-load .env if present
if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1090,SC1091
    source "$REPO_ROOT/.env"
    set +a
fi

COMMON_USER="${JENKINS_USER:-kmom88}"

if [ "$TARGET" = "local" ]; then
    export JENKINS_URL="http://192.168.30.206:8080"
    export BUILDFARM_CONFIG_URL="http://192.168.30.202:8088/ros_buildfarm_config/index-local.yaml"
    export APT_REPO_URL="http://192.168.30.202:8088/ubuntu/testing"
    export JENKINS_USER="$COMMON_USER"
    export JENKINS_TOKEN="${LOCAL_JENKINS_TOKEN:-$JENKINS_TOKEN}"

    echo "=================================================="
    echo " Activating Target: LOCAL BUILDFARM CLUSTER"
    echo " Jenkins:     $JENKINS_URL"
    echo " User:        $JENKINS_USER"
    echo " APT / Nginx: http://192.168.30.202:8088"
    echo " Config URL:  $BUILDFARM_CONFIG_URL"
    echo "=================================================="
elif [ "$TARGET" = "remote" ]; then
    export JENKINS_URL="https://build.test.ros2.org"
    export BUILDFARM_CONFIG_URL="https://raw.githubusercontent.com/rep159-testing/ros_buildfarm_config/rep159/index-rep159.yaml"
    export APT_REPO_URL="http://repo.test.ros2.org/ubuntu/testing"
    
    # Use TEST_BUILDFARM_TOKEN if set, else fallback to JENKINS_TOKEN
    REMOTE_TOKEN="${TEST_BUILDFARM_TOKEN:-$JENKINS_TOKEN}"
    export TEST_BUILDFARM_USER="${TEST_BUILDFARM_USER:-$COMMON_USER}"
    export TEST_BUILDFARM_TOKEN="$REMOTE_TOKEN"
    export JENKINS_USER="$TEST_BUILDFARM_USER"
    export JENKINS_TOKEN="$REMOTE_TOKEN"

    echo "=================================================="
    echo " Activating Target: REMOTE TEST BUILDFARM"
    echo " Jenkins:     $JENKINS_URL"
    echo " User:        $TEST_BUILDFARM_USER"
    echo " APT Repo:    $APT_REPO_URL"
    echo " Config URL:  $BUILDFARM_CONFIG_URL"
    echo "=================================================="
else
    echo "Usage: source $(basename "$0") [local|remote]"
    return 1 2>/dev/null || exit 1
fi

echo "Environment successfully configured for: $TARGET"
