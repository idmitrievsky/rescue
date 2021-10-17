#!/bin/sh -e

export SOURCE_FILES="enact tests example"
set -x

autoflake --in-place --recursive $SOURCE_FILES
isort --project=enact $SOURCE_FILES
black $SOURCE_FILES
