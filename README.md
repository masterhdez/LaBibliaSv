# La Biblia Sv (Escritorio)

Lector de la Biblia para **Linux Mint / Ubuntu / Debian**, equivalent a la app
Android: incluye las versiones **RV1960**, **NTV**, **NVI** y **PDT**, con una
interfaz **Material Design** (sombras, efectos, animaciones e iconos **Font
Awesome**) renderizada con **WebKit2**, búsqueda, resaltados, notas, marcadores,
copiar/compartir versículos y generador de stickers (color, tamaño, letra de
carta e imagen de fondo desde la galería).

## Requisitos

- Linux Mint / Ubuntu / Debian con GTK3, WebKitGTK y Python 3 (probado en Mint con Python 3.12).
- Dependencias (Debian/Ubuntu/Mint):

```
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-pango-1.0 python3-cairo gir1.2-webkit2-4.1
```

## Instalación

```
cd LaBibliaSv
./instalar.sh
```

El instalador pide `sudo`, instala las dependencias (usa
`gir1.2-webkit2-4.1`; si no existe en tu distro, prueba con `4.0`) y crea el
lanzador **"La Biblia Sv"** en el menú de aplicaciones.

## Paquete .deb instalable

```
cd LaBibliaSv
./crear_deb.sh
sudo apt install ./dist/la-biblia-sv_1.0.0_amd64.deb
```

Genera `dist/la-biblia-sv_1.0.0_amd64.deb` con la app instalada en
`/usr/share/la-biblia-sv`, lanzador en `/usr/bin/la-biblia-sv` y
**`logo.png` como icono del menú** (instalada en
`/usr/share/icons/hicolor/…/apps/la-biblia-sv.png`). La entrada de menú queda
**"La Biblia Sv"** en Linux Mint, Ubuntu, Debian y derivados.

Para desinstalar: `sudo apt remove la-biblia-sv`.

## Ejecutar manualmente

```
python3 la_biblia_sv.py
```

La ventana es **normal, redimensionable, con minimizar / maximizar / cerrar** y
arranca maximizada. Atajos:

| Tecla / botón | Acción |
| ------------- | ------ |
| `F11` o `⛶` | Alternar pantalla completa |
| `Esc`        | Salir de pantalla completa |

## Funciones

- **Interfaz Material Design** estilo Android: sombras, ripples, animaciones,
  modo oscuro y **iconos Font Awesome** (integrado en el HTML).
- **4 versiones** de la Biblia conmutables desde la barra superior.
- **Lista de libros** (AT / NT) y **marcadores**.
- Navegación **‹ Anterior / Siguiente ›** por capítulos; un toque selecciona el versículo
  y muestra la **barra de acciones** (copiar, compartir, resaltar, nota, marcador).
- **A− / A+** para cambiar el tamaño del texto (se guarda).
- **Letra del versículo**: predeterminada, **letra de carta**, manuscrita, desenfadada,
  elegante y moderna (5 fuentes TTF incluidas y embebidas en el HTML).
- **Buscar** palabras o frases (mín. 3 letras) con resultados enlazados.
- **Resaltar** versículos con 6 colores; **Quitar resaltado**.
- **Nota** personal por versículo (se guarda en la base de datos).
- **Marcador** de versículo y pestaña de marcadores.
- **Copiar** el versículo y **Compartir** (copia + abre el generador de stickers).
- **Stickers**: color de fondo (paleta), tamaño, fuente (incluye las 5
  tipografías instaladas y **letra de carta**), **imagen de fondo desde la
  galería**, guardar PNG (`~/Pictures/Biblia_Sv_sticker.png`) y copiar texto.

## Datos

- La base de datos `biblia.db` se copia la primera vez a
  `~/.local/share/LaBibliaSv/biblia.db` (no se modifica la original).
- Las preferencias se guardan en `~/.local/share/LaBibliaSv/prefs.json`.
- Las fuentes del bundle se copian a `~/.local/share/fonts` al iniciar.

## Estructura

```
LaBibliaSv/
├── la_biblia_sv.py     # App GTK3 + WebKit2 (puente Python ↔ JS)
├── biblia.db           # Base de datos (66 libros, 4 versiones)
├── logo.png            # Icono de la app
├── ui/
│   ├── index.html      # Plantilla HTML (Material)
│   ├── style.css       # Estilos Material (sombras, ripple, dark)
│   └── app.js          # Lógica UI + puente messageHandlers.biblia
├── fonts/              # Fuentes del bundle (5 estilos + Font Awesome)
├── instalar.sh         # Instalador + lanzador del menú
└── crear_deb.sh        # Empaqueta la app en un .deb instalable
```

## Registro de cambios

Consultar `REGISTRO_DE_CAMBIOS.md` en la carpeta principal del proyecto.