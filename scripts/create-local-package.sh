#/bin/sh

# https://forum.sublimetext.com/t/install-package-manually/6737/4
set -e

if [ -n "$1" ]; then
  git archive --format=zip --prefix=AutoDarkLinux/ "$1" >AutoDarkLinux.sublime-package
else
  echo "No version specified. Archiving current branch"

  trap 'git checkout main; git branch -D release' 'EXIT'

  git checkout -B release
  git submodule update --init --checkout sublime_lib
  mv sublime_lib sublime_lib_tmp
  git rm -r --cached sublime_lib
  rm -rf sublime_lib_tmp/.git
  mv sublime_lib_tmp sublime_lib
  git add sublime_lib
  git archive --format=zip --prefix=AutoDarkLinux/ release >AutoDarkLinux.sublime-package
  git submodule deinit sublime_lib
fi

echo -e '\n===Archive created. Copy it to your "Installed Packages" folder or "User" folder===\n'
