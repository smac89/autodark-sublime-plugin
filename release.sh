#!/bin/bash

set -e

[ -z "$1" ] && echo "No version specified" && exit 1

trap 'git checkout main; git branch -D release' 'EXIT'

git checkout -B release
git submodule update --init --checkout sublime_lib
mv sublime_lib sublime_lib_tmp
git rm -r --cached sublime_lib
rm -rf sublime_lib_tmp/.git
mv sublime_lib_tmp sublime_lib
git add sublime_lib
git commit -m "release for $1"
git tag "$1"
git submodule deinit sublime_lib
echo -e '\n===Tag created. Run `git push --tags`===\n'
