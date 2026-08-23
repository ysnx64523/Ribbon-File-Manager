#!/usr/bin/env bash
# Build an AppImage for Ribbon File Manager on Linux.
#
# Requirements:
#   - PyGObject + GTK3 development libraries installed on the build host
#   - appimagetool (https://github.com/AppImage/appimagetool)
#
# Usage:
#   bash pack/appimage/build.sh
#
# The produced file is written to dist/RibbonFileManager-<VERSION>-x86_64.AppImage
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(cd "$ROOT" && python3 -c 'import sys; sys.path.insert(0,"src"); import ribbonfm; print(ribbonfm.__version__)')"
APPIMAGE_TOOL="${APPIMAGE_TOOL:-appimagetool}"

BUILD="$ROOT/build/appimage/AppDir"
STAGE="$ROOT/dist"

# Clean and prepare
rm -rf "$BUILD" "$STAGE"
mkdir -p "$BUILD" "$STAGE" "$BUILD/usr/bin" "$BUILD/usr/share/applications" \
         "$BUILD/usr/share/icons/hicolor/scalable/apps" "$BUILD/usr/share/metainfo"

# Install the Python package into a staging prefix
python3 -m pip install --prefix "$BUILD/usr" "$ROOT"

# Desktop file and icon
cp "$ROOT/data/org.ribbonfm.RibbonFM.desktop" "$BUILD/usr/share/applications/"
cp "$ROOT/data/org.ribbonfm.RibbonFM.svg" "$BUILD/usr/share/icons/hicolor/scalable/apps/"
cp "$ROOT/data/org.ribbonfm.RibbonFM.metainfo.xml" "$BUILD/usr/share/metainfo/"

# Console entry point (adjust shebang and set PYTHONPATH)
console="$BUILD/usr/bin/ribbonfm"
cat > "$BUILD/AppRun" <<EOF
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\$0")")"
export PYTHONPATH="\$HERE/usr/lib/python?/site-packages:\$PYTHONPATH"
export PATH="\$HERE/usr/bin:\$PATH"
exec "\$HERE/usr/bin/ribbonfm" "\$@"
EOF
chmod +x "$BUILD/AppRun"
cp "$ROOT/data/org.ribbonfm.RibbonFM.svg" "$BUILD/ribbonfm.svg"

# Bundle icons
cat > "$BUILD/ribbonfm.desktop" <<EOF
[Desktop Entry]
Name=Ribbon File Manager
Comment=Cross-platform Ribbon-style file manager
Exec=AppRun
Terminal=false
Type=Application
Icon=org.ribbonfm.RibbonFM
Categories=System;FileTools;Utility;
EOF

# Pack it
"$APPIMAGE_TOOL" "$BUILD" "$STAGE/RibbonFileManager-$VERSION-x86_64.AppImage"

echo "Built: $STAGE/RibbonFileManager-$VERSION-x86_64.AppImage"
