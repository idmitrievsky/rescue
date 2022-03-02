#!/bin/sh -e

export SOURCE_FILES="rescue tests"
set -x

autoflake --in-place --recursive $SOURCE_FILES
isort --project=rescue $SOURCE_FILES
black $SOURCE_FILES
