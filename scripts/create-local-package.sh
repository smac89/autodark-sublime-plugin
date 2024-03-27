#/bin/sh

# https://forum.sublimetext.com/t/install-package-manually/6737/4
set -e

if [ -n "$1" ]; then
  echo "Creating archive for $1"
  git archive --format=zip --prefix=AutoDarkLinux/ "$1" --output AutoDarkLinux.sublime-package
else
  echo "No version specified. Archiving main branch" >&2
  git archive --format=zip main --output AutoDarkLinux.sublime-package
fi

unzip -l AutoDarkLinux.sublime-package
echo -e '\n===Archive created. Copy it to your "Installed Packages" folder===\n'
