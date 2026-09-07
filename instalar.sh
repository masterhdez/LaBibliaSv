#!/bin/bash
# Instalador de "La Biblia Sv" para Linux Mint / Ubuntu / Debian.
# Instala dependencias y crea un lanzador en el menú de aplicaciones.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Instalando dependencias (pide contraseña sudo)..."
sudo apt-get update
sudo apt-get install -y \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-pango-1.0 \
    python3-cairo \
    gir1.2-webkit2-4.1 || {
        echo "gir1.2-webkit2-4.1 no disponible, probando con 4.0...";
        sudo apt-get install -y python3-gi gir1.2-gtk-3.0 gir1.2-pango-1.0 python3-cairo gir1.2-webkit2-4.0;
    }

echo "==> Marcando el script como ejecutable..."
chmod +x "$DIR/la_biblia_sv.py"

echo "==> Creando lanzador en el menú de aplicaciones..."
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/la-biblia-sv.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=La Biblia Sv
GenericName=Biblia
Comment=Lector de la Biblia: RV1960, NTV, NVI y PDT
Exec=python3 $DIR/la_biblia_sv.py
Icon=$DIR/logo.png
Terminal=false
StartupNotify=true
Categories=Utility;Education;Office;
Keywords=biblia;lectura;versiculo;religion;
DESKTOP

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "Listo."
echo "  - Menú de aplicaciones: busca 'La Biblia Sv'"
echo "  - Terminal:             python3 $DIR/la_biblia_sv.py"
echo "  - Atajos:               F11 (o botón ⛶) alterna pantalla completa"