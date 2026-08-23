#!/usr/bin/env bash
# Build a self-contained AppImage (bundles GTK via PyInstaller).
# Produces: dist/RibbonFileManager-<VERSION>-x86_64.AppImage
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -1)"
[ -n "$VERSION" ] || VERSION="0.1.0"
APPIMAGE_TOOL="${APPIMAGE_TOOL:-appimagetool}"
# appimagetool AppImage needs FUSE; fall back to extract-and-run on runners.
export APPIMAGE_EXTRACT_AND_RUN="${APPIMAGE_EXTRACT_AND_RUN:-1}"

VENV="$ROOT/build/appimage-venv"
PYPKG="$ROOT/build/pyinstaller/RibbonFM"
BUILD="$ROOT/build/appimage/AppDir"
STAGE="$ROOT/dist"
PKG_ID="org.ribbonfm.RibbonFM"

rm -rf "$VENV" "$ROOT/build/pyinstaller" "$BUILD" "$STAGE"
mkdir -p "$STAGE"

echo "== Build self-contained bundle (PyInstaller) =="
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip pyinstaller
"$VENV/bin/python" -m PyInstaller "$ROOT/pack/linux/ribbonfm_linux.spec" \
  --distpath "$ROOT/build/pyinstaller" \
  --workpath "$ROOT/build/pyinstaller/work" \
  --noconfirm

echo "== Assemble AppDir =="
mkdir -p "$BUILD/usr/lib/ribbonfm" \
         "$BUILD/usr/share/applications" \
         "$BUILD/usr/share/icons/hicolor/scalable/apps"
cp -r "$PYPKG/." "$BUILD/usr/lib/ribbonfm/"

cat > "$BUILD/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/ribbonfm/RibbonFM" "$@"
EOF
chmod +x "$BUILD/AppRun"

cp "$ROOT/data/$PKG_ID.desktop" "$BUILD/usr/share/applications/$PKG_ID.desktop"
cp "$ROOT/data/$PKG_ID.svg" "$BUILD/usr/share/icons/hicolor/scalable/apps/$PKG_ID.svg"
cp "$ROOT/data/$PKG_ID.metainfo.xml" "$BUILD/usr/share/metainfo/" 2>/dev/null || true

cat > "$BUILD/$PKG_ID.desktop" <<EOF
[Desktop Entry]
Name=Ribbon File Manager
Name[zh_CN]=Ribbon 文件管理器
Comment=Cross-platform Ribbon-style file manager
Exec=AppRun
Terminal=false
Type=Application
Icon=$PKG_ID
Categories=System;FileTools;Utility;
EOF
cp "$ROOT/data/$PKG_ID.svg" "$BUILD/$PKG_ID.svg"

echo "== appimagetool =="
"$APPIMAGE_TOOL" "$BUILD" "$STAGE/RibbonFileManager-$VERSION-x86_64.AppImage"
echo "Built: $STAGE/RibbonFileManager-$VERSION-x86_64.AppImage"
