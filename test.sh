#!/bin/bash

VENV=/tmp/jvr/venv
TESTVENV=/tmp/jvr/testvenv

set -e -x

rm -rf "$VENV" "$TESTVENV" dist wheelhouse

python3 -m venv "$VENV"
source "$VENV"/bin/activate

pip install --upgrade pip build

echo; echo; echo

python3 -m build

deactivate

ls dist/*.whl

python3 -m venv "$TESTVENV"
source "$TESTVENV"/bin/activate

pip install dist/*.whl

# DIR="$PWD"

# cd /tmp/jvr
# rm -rf testvenv
# python3 -m venv testvenv
# # source testvenv/bin/activate
# # pip install "$DIR"'[test]'
# # echo; echo; echo
# # pytest -v "$DIR"
# # python --version