#!/bin/sh -e

export SOURCE_FILES="rescue tests"
set -x

black --check --diff $SOURCE_FILES
flake8 $SOURCE_FILES
mypy $SOURCE_FILES --show-traceback
isort --check --diff --project=rescue $SOURCE_FILES
