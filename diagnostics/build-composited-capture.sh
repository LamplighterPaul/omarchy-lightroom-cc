#!/bin/bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
data=${LRCC_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-lightroom-cc}
protocol="$data/tools/weston/usr/share/libweston-15/protocols/weston-output-capture.xml"
build="$data/tools/capture-build"
mkdir -p "$build"
wayland-scanner client-header "$protocol" "$build/weston-output-capture-client-protocol.h"
wayland-scanner private-code "$protocol" "$build/weston-output-capture-protocol.c"
read -r -a dependencies < <(pkg-config --cflags --libs wayland-client libpng)
cc -O2 -Wall -I"$build" "$source_dir/composited-capture.c" \
  "$build/weston-output-capture-protocol.c" -o "$build/composited-capture.new" "${dependencies[@]}"
# Rename avoids replacing the contents of an executable that is still running.
mv "$build/composited-capture.new" "$data/tools/composited-capture"
