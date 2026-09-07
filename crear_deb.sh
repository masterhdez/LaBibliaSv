#!/bin/bash
# Empaqueta "La Biblia Sv" en un instalable .deb para Linux Mint / Ubuntu / Debian.
# El icono del menú usa logo.png (instalado en /usr/share/icons/hicolor/...).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

VERSION="1.0.0"
ARCH="$(dpkg --print-architecture)"
PACKAGE="la-biblia-sv"
OUT="$PACKAGE"_"$VERSION"_"$ARCH"
STAGE="$(mktemp -d /tmp/opencode/pkg.XXXXXX)/$OUT"
mkdir -p "$STAGE"

DEST="$STAGE/usr/share/$PACKAGE"
ICONS="$STAGE/usr/share/icons/hicolor"
APPL="$STAGE/usr/share/applications"
BIN="$STAGE/usr/bin"
mkdir -p "$DEST/ui" "$DEST/fonts" "$ICONS" "$APPL" "$BIN" "$STAGE/DEBIAN"

# --- Datos de la app -------------------------------------------------------
cp la_biblia_sv.py biblia.db logo.png "$DEST/"
cp ui/index.html ui/style.css ui/app.js "$DEST/ui/"
cp fonts/*.ttf "$DEST/fonts/"

# --- Icono del menú (logo.png a los tamaños hicolor) -----------------------
python3 - "$DEST/logo.png" "$ICONS" <<'PY'
import os, sys
from PIL import Image
src, icons = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA")
for size in (16, 22, 24, 32, 48, 64, 128, 256, 512):
    d = os.path.join(icons, "%dx%d" % (size, size), "apps")
    os.makedirs(d, exist_ok=True)
    im.resize((size, size), Image.LANCZOS).save(os.path.join(d, "la-biblia-sv.png"))
PY

# --- Lanzador y entrada de menú ---------------------------------------------
cat > "$BIN/la-biblia-sv" <<'SH'
#!/bin/sh
exec python3 /usr/share/la-biblia-sv/la_biblia_sv.py "$@"
SH
chmod 755 "$BIN/la-biblia-sv"

cat > "$APPL/la-biblia-sv.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=La Biblia Sv
GenericName=Biblia
Comment=Lector de la Biblia: RV1960, NTV, NVI y PDT
Exec=la-biblia-sv
Icon=la-biblia-sv
Terminal=false
StartupNotify=true
StartupWMClass=La Biblia Sv
Categories=Utility;Education;Office;
Keywords=biblia;lectura;versiculo;religion;
DESKTOP

# --- Metadatos del paquete ---------------------------------------------------
SIZE_KB="$(du -sk "$STAGE" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<CONTROL
Package: $PACKAGE
Version: $VERSION
Section: education
Priority: optional
Architecture: $ARCH
Maintainer: Agdala <agdala.sv@gmail.com>
Installed-Size: $SIZE_KB
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-pango-1.0, python3-cairo, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0
Description: Lector de la Biblia (RV1960, NTV, NVI y PDT)
 Lector de la Biblia con interfaz Material Design estilo Android:
 multiples versiones, búsqueda, resaltados, notas, marcadores,
 copiar/compartir versículos y generador de stickers.
 Powered by Agdala 2026.
CONTROL

cat > "$STAGE/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
exit 0
POST
chmod 755 "$STAGE/DEBIAN/postinst"

# --- Construcción -------------------------------------------------------------
mkdir -p dist
dpkg-deb --build --root-owner-group "$STAGE" "dist/$OUT.deb"
rm -rf "$(dirname "$STAGE")"

echo ""
echo "Paquete creado: dist/$OUT.deb"
echo "Instalar con:   sudo apt install ./dist/$OUT.deb"
echo "Desinstalar:    sudo apt remove la-biblia-sv"