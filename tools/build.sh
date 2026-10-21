#!/bin/zsh
#  tools/build.sh:  build the juno kernel to out/juno.jam.
#
#  juno is its own repository but has no compiler of its own:  it
#  is built by jock's tools/kern.sh, which emits a bootable trap
#  whose four arms land on Arvo's axes.  Point JOCK at a jock
#  checkout.
#
#  Each library DIRECTORY is a separate --data-dir:  jock's
#  tools/libs.py globs *.jock one level deep and does not recurse,
#  and a module's name is its bare filename, so the names must be
#  unique across every directory passed.
set -e
JOCK=${JOCK:-$HOME/Code/jock}
ROOT="${0:A:h:h}"
[[ -x "$JOCK/tools/kern.sh" ]] || {
  echo "build.sh: no jock checkout at $JOCK (set JOCK=...)" >&2; exit 2; }
mkdir -p "$ROOT/out"
zsh "$JOCK/tools/kern.sh" \
  --data-dir "$ROOT/pkg/juno/sys/lib" \
  --data-dir "$ROOT/pkg/juno/sys/vane" \
  "$ROOT/pkg/juno/sys/juno.jock" "$ROOT/out/juno.jam"
