#!/usr/bin/env bash
# Build a **fully self-contained** .deb that bundles GTK3 + PyGObject (via
# PyInstaller). No system python3-gi / gir1.2-gtk-3.0 dependency at runtime.
# Produces: build/deb/RibbonFM_<VERSION>_amd64.deb
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(printf '%s' "${GITHUB_REF_NAME:-}" | sed 's/^v//')"
[ -n "$VERSION" ] || VERSION="$(git -C "$ROOT" describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')"
[ -n "$VERSION" ] || VERSION="0.1.0"
# Emit the version for the packaged app (PyInstaller doesn't run setuptools_scm).
printf '__version__ = "%s"\n' "$VERSION" > "$ROOT/src/ribbonfm/_version.py"
PKG_ID="org.ribbonfm.RibbonFM"
OUT="$ROOT/build/deb"
DIST="$ROOT/build/pyinstaller/RibbonFM"
VENV="$ROOT/build/venv"

rm -rf "$OUT" "$ROOT/build/pyinstaller" "$VENV"
mkdir -p "$OUT"

echo "== Prepare build venv (system site packages => gi available) =="
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip pyinstaller

echo "== Build translation catalogs (so .mo are bundled) =="
"$VENV/bin/python" "$ROOT/tools/gen_po.py"

echo "== PyInstaller (bundled GTK/PyGObject) =="
"$VENV/bin/python" -m PyInstaller "$ROOT/pack/linux/ribbonfm_linux.spec" \
  --distpath "$ROOT/build/pyinstaller" \
  --workpath "$ROOT/build/pyinstaller/work" \
  --noconfirm

STAGE="$OUT/pkg"
rm -rf "$STAGE"
mkdir -p "$STAGE/opt/ribbonfm" \
         "$STAGE/usr/bin" \
         "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/scalable/apps" \
         "$STAGE/usr/share/metainfo" \
         "$STAGE/DEBIAN"

cp -r "$DIST/." "$STAGE/opt/ribbonfm/"

cat > "$STAGE/usr/bin/ribbonfm" <<'EOF'
#!/bin/sh
exec /opt/ribbonfm/RibbonFM "$@"
EOF
chmod +x "$STAGE/usr/bin/ribbonfm"

cp "$ROOT/data/$PKG_ID.desktop" "$STAGE/usr/share/applications/"
cp "$ROOT/data/$PKG_ID.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/$PKG_ID.svg"
cp "$ROOT/data/$PKG_ID.metainfo.xml" "$STAGE/usr/share/metainfo/"

# Self-contained: no python3-gi / gir1.2-gtk-3.0 dependency (only libc).
cat > "$STAGE/DEBIAN/control" <<EOF
Package: ribbonfm
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6
Maintainer: RibbonFM contributors <noreply@example.com>
Description: Windows-Explorer-like Ribbon file manager
 RibbonFM is a cross-platform file manager with a Windows-Explorer-like
 Ribbon toolbar, written in Python with GTK3 (PyGObject). This package is
 self-contained and bundles the GTK runtime.
EOF

dpkg-deb --build "$STAGE" "$OUT/RibbonFM_${VERSION}_amd64.deb"
echo "Built: $OUT/RibbonFM_${VERSION}_amd64.deb"
