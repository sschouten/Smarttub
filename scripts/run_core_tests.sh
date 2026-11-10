#!/usr/bin/env bash
# Run this repository's tests inside the Home Assistant core test harness.
#
# usage: scripts/run_core_tests.sh [HA_VERSION]   (default: 2026.10.4)
# requires: git, uv (https://docs.astral.sh/uv/)
set -euo pipefail

HA_VERSION="${1:-2026.10.4}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK_DIR="${WORK_DIR:-$REPO_DIR/.core}"

if [ ! -d "$WORK_DIR/.git" ]; then
  git clone --depth 1 --branch "$HA_VERSION" --filter=blob:none --sparse \
    https://github.com/home-assistant/core.git "$WORK_DIR"
fi
cd "$WORK_DIR"
git sparse-checkout set --no-cone \
  '/tests/*.py' '/tests/components/*.py' '/tests/test_util/' '/tests/testing_config/' \
  '/tests/components/diagnostics/' '/tests/components/recorder/' \
  '/tests/helpers/__init__.py' '/requirements_test.txt' \
  '/homeassistant/package_constraints.txt' '/pyproject.toml' \
  '/packages/pytest-homeassistant/'

PYTHON_VERSION="$(sed -n 's/^requires-python *= *">=\([0-9.]*\)".*/\1/p' pyproject.toml | cut -d. -f1,2)"
if [ ! -d .venv ]; then
  uv venv -p "$PYTHON_VERSION" .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
grep -vE '^-[cr]|mypy|pylint|astroid|prek|codspeed|librt|ast-serialize' \
  requirements_test.txt > .req-test.txt
uv pip install -q "homeassistant==$HA_VERSION" "python-smarttub>=0.0.47" \
  paho-mqtt aiohasupervisor -r .req-test.txt -c homeassistant/package_constraints.txt
# Home Assistant 2026.11+ keeps its test helpers in a separate package
# and no longer has tests.common; this repository's tests import the old paths
if [ -d packages/pytest-homeassistant ]; then
  uv pip install -q --no-deps -e packages/pytest-homeassistant
  shim() {
    [ -e "$1" ] && return
    echo "import sys, $2 as _m; sys.modules[__name__] = _m" > "$1"
  }
  shim tests/common.py pytest_homeassistant.common
  shim tests/typing.py pytest_homeassistant.typing
  grep -q get_diagnostics_for_config_entry tests/components/diagnostics/__init__.py ||
    echo "from pytest_homeassistant.components.diagnostics import get_diagnostics_for_config_entry  # noqa: F401" \
      >> tests/components/diagnostics/__init__.py
fi

# replace the built-in component and its tests with this repository's version
SITE="$(python -c 'import homeassistant, os; print(os.path.dirname(homeassistant.__file__))')"
rm -rf "$SITE/components/smarttub" tests/components/smarttub
cp -r "$REPO_DIR/custom_components/smarttub" "$SITE/components/smarttub"
cp -r "$REPO_DIR/tests" tests/components/smarttub

python -m pytest tests/components/smarttub -q -p no:sugar
