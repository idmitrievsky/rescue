#!/bin/sh -e

set -ex

scripts/check.sh
coverage run -m hammett tests
scripts/coverage.sh
