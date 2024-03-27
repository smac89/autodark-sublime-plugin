#!/bin/bash

set -e

[ -z "$1" ] && echo "No version specified" >&2 && exit 1
git tag "$1"
echo -e '\n===Tag created. Run `git push --tags`===\n'
