#!/bin/sh -e

set -x

coverage report
coverage html
