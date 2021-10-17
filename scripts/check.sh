#!/bin/sh -e

export SOURCE_FILES="enact tests example"
set -x

black --check --diff $SOURCE_FILES
flake8 $SOURCE_FILES
mypy $SOURCE_FILES
isort --check --diff --project=enact $SOURCE_FILES
