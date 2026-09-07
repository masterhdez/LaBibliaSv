#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La Biblia Sv — lector de la Biblia para escritorio (Linux Mint / Ubuntu / Debian).

UI moderna estilo Android (Material Design) renderizada con WebKit2:
sombras, efectos, animaciones y iconos Font Awesome; ventana normal
redimensionable con minimizar/maximizar/cerrar.

Dependencias (Debian/Ubuntu/Mint):
    sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-pango-1.0 \
                     python3-cairo gir1.2-webkit2-4.1
Uso:
    python3 la_biblia_sv.py
"""

import base64
import json
import os
import shutil
import sqlite3

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("PangoCairo", "1.0")
try:
    gi.require_version("WebKit2", "4.1")
except ValueError:
    gi.require_version("WebKit2", "4.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango, PangoCairo, WebKit2

APP_NAME = "La Biblia Sv"
DB_FILENAME = "biblia.db"
PREFS_FILENAME = "prefs.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

VERSIONS = [
    ("rv", "Reina-Valera 1960"),
    ("ntv", "Nueva Traducción Viviente"),
    ("nvi", "Nueva Versión Internacional 2015"),
    ("pdt", "La Palabra de Dios para Todos"),
]

# Letras del versículo (id -> family CSS). Pref: 'verse_font'.
VERSE_FONTS = {
    "default": "Georgia, 'Segoe UI', serif",
    "greatvibes": "'LBS GreatVibes', Georgia, serif",
    "dancing": "'LBS Dancing', Georgia, serif",
    "caveat": "'LBS Caveat', Georgia, serif",
    "playfair": "'LBS Playfair', Georgia, serif",
    "oswald": "'LBS Oswald', sans-serif",
}

# Fuentes empaquetadas (family -> archivo TTF en fonts/)
FONT_BUNDLE = {
    "FontAwesome": "fa_solid.ttf",
    "LBS GreatVibes": "GreatVibes-Regular.ttf",
    "LBS Dancing": "Dance.ttf",
    "LBS Caveat": "Caveat.ttf",
    "LBS Playfair": "Playfair.ttf",
    "LBS Oswald": "Oswald.ttf",
}

ABBR = {
    1: "Gn", 2: "Ex", 3: "Lv", 4: "Nm", 5: "Dt", 6: "Jos", 7: "Jue",
    8: "Rt", 9: "1 S", 10: "2 S", 11: "1 R", 12: "2 R", 13: "1 Cr",
    14: "2 Cr", 15: "Esd", 16: "Neh", 17: "Est", 18: "Job", 19: "Sal",
    20: "Pr", 21: "Ec", 22: "Cnt", 23: "Is", 24: "Jer", 25: "Lm",
    26: "Ez", 27: "Dn", 28: "Os", 29: "Jl", 30: "Am", 31: "Abd",
    32: "Jon", 33: "Miq", 34: "Nah", 35: "Hab", 36: "Sof", 37: "Hag",
    38: "Zac", 39: "Mal", 40: "Mt", 41: "Mr", 42: "Lc", 43: "Jn",
    44: "Hch", 45: "Ro", 46: "1 Co", 47: "2 Co", 48: "Gá", 49: "Ef",
    50: "Fil", 51: "Col", 52: "1 Ts", 53: "2 Ts", 54: "1 Ti", 55: "2 Ti",
    56: "Tit", 57: "Flm", 58: "He", 59: "Stg", 60: "1 P", 61: "2 P",
    62: "1 Jn", 63: "2 Jn", 64: "3 Jn", 65: "Jud", 66: "Ap",
}

HIGHLIGHT_COLORS = [
    ("yellow", "#FFE9A8"),
    ("green", "#9ED3AE"),
    ("blue", "#9FC4E8"),
    ("pink", "#EEB3D0"),
    ("purple", "#CB9DE0"),
    ("orange", "#F2B291"),
]


def data_dir():
    home = os.path.expanduser("~")
    path = os.path.join(home, ".local", "share", "LaBibliaSv")
    os.makedirs(path, exist_ok=True)
    return path


def prefs_path():
    return os.path.join(data_dir(), PREFS_FILENAME)


def db_user_path():
    return os.path.join(data_dir(), DB_FILENAME)


def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


class Prefs:
    def __init__(self):
        self.data = {
            "version": "nvi",
            "book": 1,
            "chapter": 1,
            "verse": 1,
            "text_size": 19,
            "theme": "system",
            "verse_font": "default",
        }
        self.load()

    def load(self):
        try:
            with open(prefs_path(), "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except Exception:
            pass

    def save(self):
        try:
            with open(prefs_path(), "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


class BibleDB:
    """Capa de datos sobre biblia.db (mismo esquema que la app Android)."""

    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")

    def books(self):
        return self.conn.execute(
            "SELECT id, name, order_no, testament FROM books ORDER BY order_no"
        ).fetchall()

    def chapters(self, version, book_id):
        row = self.conn.execute(
            "SELECT COUNT(DISTINCT chapter) AS n FROM verses "
            "WHERE version=? AND book_id=?",
            (version, book_id),
        ).fetchone()
        return row["n"] if row else 0

    def verses(self, version, book_id, chapter):
        rows = self.conn.execute(
            "SELECT verse, text, notes FROM verses "
            "WHERE version=? AND book_id=? AND chapter=? ORDER BY verse",
            (version, book_id, chapter),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_highlight(self, version, book_id, chapter, verse):
        row = self.conn.execute(
            "SELECT color FROM highlights WHERE version=? AND book_id=? "
            "AND chapter=? AND verse=?",
            (version, book_id, chapter, verse),
        ).fetchone()
        return row["color"] if row else None

    def set_highlight(self, version, book_id, chapter, verse, color):
        self.conn.execute(
            "INSERT OR REPLACE INTO highlights "
            "(version, book_id, chapter, verse, color) VALUES (?,?,?,?,?)",
            (version, book_id, chapter, verse, color),
        )
        self.conn.commit()

    def remove_highlight(self, version, book_id, chapter, verse):
        self.conn.execute(
            "DELETE FROM highlights WHERE version=? AND book_id=? "
            "AND chapter=? AND verse=?",
            (version, book_id, chapter, verse),
        )
        self.conn.commit()

    def is_bookmarked(self, version, book_id, chapter, verse):
        row = self.conn.execute(
            "SELECT 1 FROM bookmarks WHERE version=? AND book_id=? "
            "AND chapter=? AND verse=? LIMIT 1",
            (version, book_id, chapter, verse),
        ).fetchone()
        return row is not None

    def toggle_bookmark(self, version, book_id, chapter, verse):
        if self.is_bookmarked(version, book_id, chapter, verse):
            self.conn.execute(
                "DELETE FROM bookmarks WHERE version=? AND book_id=? "
                "AND chapter=? AND verse=?",
                (version, book_id, chapter, verse),
            )
            marked = False
        else:
            self.conn.execute(
                "INSERT INTO bookmarks (version, book_id, chapter, verse) "
                "VALUES (?,?,?,?)",
                (version, book_id, chapter, verse),
            )
            marked = True
        self.conn.commit()
        return marked

    def bookmarks(self, version):
        rows = self.conn.execute(
            "SELECT b.book_id, b.chapter, b.verse, k.name FROM bookmarks b "
            "JOIN books k ON k.id = b.book_id "
            "WHERE b.version=? ORDER BY b.book_id, b.chapter, b.verse",
            (version,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_note(self, version, book_id, chapter, verse):
        row = self.conn.execute(
            "SELECT note FROM user_notes WHERE version=? AND book_id=? "
            "AND chapter=? AND verse=? LIMIT 1",
            (version, book_id, chapter, verse),
        ).fetchone()
        return row["note"] if row else None

    def save_note(self, version, book_id, chapter, verse, note):
        exists = self.get_note(version, book_id, chapter, verse)
        if note.strip():
            if exists is None:
                self.conn.execute(
                    "INSERT INTO user_notes "
                    "(version, book_id, chapter, verse, note, created_at) "
                    "VALUES (?,?,?,?,?, strftime('%s','now'))",
                    (version, book_id, chapter, verse, note.strip()),
                )
            else:
                self.conn.execute(
                    "UPDATE user_notes SET note=? WHERE version=? AND book_id=? "
                    "AND chapter=? AND verse=?",
                    (note.strip(), version, book_id, chapter, verse),
                )
        else:
            self.conn.execute(
                "DELETE FROM user_notes WHERE version=? AND book_id=? "
                "AND chapter=? AND verse=?",
                (version, book_id, chapter, verse),
            )
        self.conn.commit()

    def search(self, version, term, limit=300):
        rows = self.conn.execute(
            "SELECT v.book_id, v.chapter, v.verse, v.text, k.name FROM verses v "
            "JOIN books k ON k.id = v.book_id "
            "WHERE v.version=? AND v.text LIKE ? "
            "ORDER BY v.book_id, v.chapter, v.verse LIMIT ?",
            (version, "%" + term + "%", limit),
        ).fetchall()
        return [dict(r) for r in rows]


def _system_fonts():
    try:
        ctx = Gtk.Label().get_pango_context()
        return [f.get_name() for f in ctx.list_families()]
    except Exception:
        return []


class StickerWindow(Gtk.Window):
    """Generador de stickers al estilo de la versión Android.

    Color de fondo, tamaño, fuente (letra de carta incluida), imagen de
    fondo desde la galería, copiar texto y guardar imagen PNG.
    """

    def __init__(self, parent, bible, version, book_id, chapter, verse, text):
        super().__init__(title="Sticker — " + APP_NAME)
        self.set_transient_for(parent)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_modal(True)
        self.set_default_size(500, 680)
        self.set_resizable(True)
        self.bible = bible

        self.verse_text = text
        self.ref = self._ref(book_id, chapter, verse, version)
        self.color = "#FFE9A8"
        self.font = None
        self.text_size = 24
        self.image_pixbuf = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        self.add(box)

        self.draw = Gtk.DrawingArea()
        self.draw.set_size_request(440, 560)
        self.draw.connect("draw", self.on_draw)
        box.pack_start(self.draw, True, True, 0)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(controls, False, False, 0)

        controls.pack_start(Gtk.Label(label="Color:"), False, False, 0)
        self.color_buttons = {}
        grp = None
        for name, hexv in HIGHLIGHT_COLORS:
            if grp is None:
                b = Gtk.RadioButton()
                grp = b
            else:
                b = Gtk.RadioButton.new_from_widget(grp)
            b.set_size_request(30, 30)
            rgba = Gdk.RGBA()
            rgba.parse(hexv)
            b.override_background_color(Gtk.StateFlags.NORMAL, rgba)
            b.connect("toggled", lambda w, c=hexv, n=name: self._pick_color(w, c, n))
            controls.pack_start(b, False, False, 0)
            self.color_buttons[name] = b
        self.color_buttons["yellow"].set_active(True)

        controls.pack_start(Gtk.Label(label="  A-"), False, False, 0)
        ssz = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 14, 40, 1)
        ssz.set_size_request(100, -1)
        ssz.set_value(self.text_size)
        ssz.connect("value-changed", self._change_size)
        controls.pack_start(ssz, False, False, 0)
        controls.pack_start(Gtk.Label(label="A+"), False, False, 0)

        controls.pack_start(Gtk.Label(label="  Letra:"), False, False, 0)
        ft = Gtk.ComboBoxText()
        fonts = ["serif", "sans", "monospace"]
        for fam in _system_fonts():
            if fam not in fonts:
                fonts.append(fam)
        for f in fonts:
            ft.append_text(f)
        ft.set_active(0)
        ft.connect("changed", self._change_font)
        controls.pack_start(ft, False, False, 0)

        img_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(img_actions, False, False, 0)

        btn_img = Gtk.Button(label="Añadir imagen de fondo")
        btn_img.connect("clicked", self._choose_image)
        img_actions.pack_start(btn_img, True, True, 0)

        btn_img_off = Gtk.Button(label="Quitar imagen")
        btn_img_off.connect("clicked", self._remove_image)
        img_actions.pack_start(btn_img_off, True, True, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(actions, False, False, 0)

        btn_save = Gtk.Button(label="Guardar imagen")
        btn_save.connect("clicked", self._save_png)
        actions.pack_start(btn_save, True, True, 0)

        btn_copy = Gtk.Button(label="Copiar texto")
        btn_copy.connect("clicked", lambda *_: self._copy_text())
        actions.pack_start(btn_copy, True, True, 0)

        btn_close = Gtk.Button(label="Cerrar")
        btn_close.connect("clicked", lambda *_: self.destroy())
        actions.pack_start(btn_close, True, True, 0)

        if os.path.exists(LOGO_PATH):
            try:
                self.set_icon_from_file(LOGO_PATH)
            except Exception:
                pass

    def _ref(self, book_id, chapter, verse, version):
        abbr = ABBR.get(book_id, str(book_id))
        vlabel = dict(VERSIONS).get(version, version)
        return "%s %s:%s (%s)" % (abbr, chapter, verse, vlabel)

    def _pick_color(self, w, hexv, name):
        if w.get_active():
            self.color = hexv
            self.draw.queue_draw()

    def _change_size(self, s):
        self.text_size = int(s.get_value())
        self.draw.queue_draw()

    def _change_font(self, cb):
        self.font = cb.get_active_text()
        self.draw.queue_draw()

    def _choose_image(self, w):
        dlg = Gtk.FileChooserDialog(
            title="Añadir imagen de fondo",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dlg.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Abrir", Gtk.ResponseType.ACCEPT,
        )
        filt = Gtk.FileFilter()
        filt.set_name("Imágenes")
        filt.add_mime_type("image/png")
        filt.add_mime_type("image/jpeg")
        filt.add_pixbuf_formats()
        dlg.add_filter(filt)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            path = dlg.get_filename()
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 1600, 1600, True)
                self.image_pixbuf = pb
                self.draw.queue_draw()
            except Exception as e:
                self._info("No se pudo cargar la imagen: %s" % e)
        dlg.destroy()

    def _remove_image(self, w):
        self.image_pixbuf = None
        self.draw.queue_draw()

    def _rounded_rect(self, cr, x, y, w, h, rad):
        rad = min(rad, w / 2, h / 2)
        cr.new_path()
        cr.arc(x + rad, y + rad, rad, 3.14159, 1.5 * 3.14159)
        cr.arc(x + w - rad, y + rad, rad, 1.5 * 3.14159, 2 * 3.14159)
        cr.arc(x + w - rad, y + h - rad, rad, 0, 0.5 * 3.14159)
        cr.arc(x + rad, y + h - rad, rad, 0.5 * 3.14159, 3.14159)
        cr.close_path()

    def _card_background(self, cr, x0, y0, cw, ch):
        if self.image_pixbuf is not None:
            pb = self.image_pixbuf
            scale = min(cw / pb.get_width(), ch / pb.get_height())
            nw = int(pb.get_width() * scale)
            nh = int(pb.get_height() * scale)
            dx = x0 + (cw - nw) // 2
            dy = y0 + (ch - nh) // 2
            cr.save()
            cr.rectangle(x0, y0, cw, ch)
            cr.clip()
            Gdk.cairo_set_source_pixbuf(cr, pb, dx, dy)
            cr.paint()
            cr.restore()

        rgba = Gdk.RGBA()
        rgba.parse(self.color)
        alpha = 0.45 if self.image_pixbuf is not None else 1.0
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, alpha)
        self._rounded_rect(cr, x0, y0, cw, ch, 22)
        cr.fill()

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        self._render_card(cr, w, h)
        return True

    def _render_card(self, cr, w, h):
        pad = 24
        x0, y0, cw, ch = pad, pad, w - 2 * pad, h - 2 * pad
        self._card_background(cr, x0, y0, cw, ch)

        brand = self.draw.create_pango_layout("Biblia Sv")
        brand.set_font_description(Pango.FontDescription.from_string("serif bold 22"))
        tw, th = brand.get_pixel_size()
        cr.move_to((w - tw) / 2.0, y0 + 26)
        cr.set_source_rgb(0.15, 0.17, 0.17)
        PangoCairo.show_layout(cr, brand)

        body = self.draw.create_pango_layout("")
        body.set_width(int((cw - 40) * Pango.SCALE))
        body.set_wrap(Pango.WrapMode.WORD_CHAR)
        fam = self.font or "serif"
        body.set_font_description(
            Pango.FontDescription.from_string("%s %d" % (fam, self.text_size))
        )
        body.set_text(self.verse_text, -1)
        btw, bth = body.get_pixel_size()

        y1 = y0 + 96
        bottom = y0 + ch - 58
        max_h = bottom - y1
        size = self.text_size
        while bth > max_h and size > 10:
            size -= 1
            body.set_font_description(
                Pango.FontDescription.from_string("%s %d" % (fam, size))
            )
            btw, bth = body.get_pixel_size()
        body_off = max(0, (max_h - bth) // 2)

        if self.image_pixbuf is not None:
            cr.set_source_rgba(0, 0, 0, 0.55)
            cr.move_to((w - btw) / 2.0 + 1, y1 + body_off + 1)
            PangoCairo.show_layout(cr, body)
            cr.set_source_rgb(1, 1, 1)
        else:
            cr.set_source_rgb(0.15, 0.17, 0.17)
        cr.move_to((w - btw) / 2.0, y1 + body_off)
        PangoCairo.show_layout(cr, body)

        ref_layout = self.draw.create_pango_layout(self.ref)
        ref_layout.set_font_description(Pango.FontDescription.from_string("sans bold 14"))
        rtw, rth = ref_layout.get_pixel_size()
        cr.set_source_rgba(0.25, 0.28, 0.28, 1.0)
        cr.move_to((w - rtw) / 2.0, y0 + ch - rth - 18)
        PangoCairo.show_layout(cr, ref_layout)

    def _draw_to_context(self, ctx, w, h):
        """Versión para PNG: renderiza sobre una superficie cairo sin widget."""
        pad = 24
        x0, y0, cw, ch = pad, pad, w - 2 * pad, h - 2 * pad
        rgba = Gdk.RGBA()
        rgba.parse("#FFFFFF")
        ctx.set_source_rgb(rgba.red, rgba.green, rgba.blue)
        ctx.rectangle(0, 0, w, h)
        ctx.fill()
        self._card_background(ctx, x0, y0, cw, ch)

        brand = self.draw.create_pango_layout("Biblia Sv")
        brand.set_font_description(Pango.FontDescription.from_string("serif bold 22"))
        tw, th = brand.get_pixel_size()
        ctx.set_source_rgb(0.15, 0.17, 0.17)
        ctx.move_to((w - tw) / 2.0, y0 + 26)
        PangoCairo.show_layout(ctx, brand)

        body = self.draw.create_pango_layout("")
        body.set_width(int((cw - 40) * Pango.SCALE))
        body.set_wrap(Pango.WrapMode.WORD_CHAR)
        sc = w / 440.0
        fam = self.font or "serif"
        base = int(self.text_size * sc)
        body.set_font_description(Pango.FontDescription.from_string("%s %d" % (fam, base)))
        body.set_text(self.verse_text, -1)
        btw, bth = body.get_pixel_size()

        y1 = y0 + 96
        bottom = y0 + ch - 58
        max_h = bottom - y1
        size = base
        while bth > max_h and size > 10:
            size -= 1
            body.set_font_description(Pango.FontDescription.from_string("%s %d" % (fam, size)))
            btw, bth = body.get_pixel_size()
        body_off = max(0, (max_h - bth) // 2)

        if self.image_pixbuf is not None:
            ctx.set_source_rgba(0, 0, 0, 0.55)
            ctx.move_to((w - btw) / 2.0 + 1, y1 + body_off + 1)
            PangoCairo.show_layout(ctx, body)
            ctx.set_source_rgb(1, 1, 1)
        else:
            ctx.set_source_rgb(0.15, 0.17, 0.17)
        ctx.move_to((w - btw) / 2.0, y1 + body_off)
        PangoCairo.show_layout(ctx, body)

        rr = self.draw.create_pango_layout(self.ref)
        rr.set_font_description(Pango.FontDescription.from_string("sans bold 14"))
        rw, rh = rr.get_pixel_size()
        ctx.set_source_rgba(0.25, 0.28, 0.28, 1.0)
        ctx.move_to((w - rw) / 2.0, y0 + ch - rh - 18)
        PangoCairo.show_layout(ctx, rr)

    def _save_png(self, *args):
        out = os.path.join(os.path.expanduser("~"), "Pictures")
        os.makedirs(out, exist_ok=True)
        path = os.path.join(out, "Biblia_Sv_sticker.png")
        try:
            import cairo

            surf = cairo.ImageSurface(cairo.Format.ARGB32, 880, 1120)
            ctx = cairo.Context(surf)
            self._draw_to_context(ctx, 880, 1120)
            surf.write_to_png(path)
            self._info("Guardado en %s" % path)
        except Exception as e:
            self._info("Error: %s" % e)

    def _info(self, msg):
        d = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=msg,
        )
        d.run()
        d.destroy()

    def _copy_text(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text("%s\n\n%s" % (self.ref, self.verse_text), -1)
        self._info("Copiado al portapapeles")


# ---------------------------------------------------------------------------
# Recursos / HTML
# ---------------------------------------------------------------------------

def prepare_assets():
    """Asegura fonts/ con FA + el bundle, los instala para el usuario y
    devuelve el CSS de las fuentes embebidas en base64."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    # Font Awesome desde el proyecto Android si aún no está
    fa = os.path.join(FONTS_DIR, "fa_solid.ttf")
    if not os.path.exists(fa):
        candidates = [
            "/home/master/Escritorio/biblia/app/src/main/res/font/fa_solid.ttf",
            os.path.join(os.path.expanduser("~"), ".local", "share", "fonts", "fa_solid.ttf"),
        ]
        for c in candidates:
            if os.path.exists(c):
                try:
                    shutil.copy(c, fa)
                except Exception:
                    pass
                break
    # Instalar todas en ~/.local/share/fonts
    dest = os.path.join(os.path.expanduser("~"), ".local", "share", "fonts")
    os.makedirs(dest, exist_ok=True)
    for f in os.listdir(FONTS_DIR):
        if f.lower().endswith((".ttf", ".otf")):
            try:
                shutil.copy(os.path.join(FONTS_DIR, f), os.path.join(dest, f))
            except Exception:
                pass
    try:
        os.system("fc-cache -f >/dev/null 2>&1")
    except Exception:
        pass
    # CSS @font-face en base64 (autocontenido)
    faces = []
    for family, fname in FONT_BUNDLE.items():
        p = os.path.join(FONTS_DIR, fname)
        if os.path.exists(p):
            faces.append(
                "@font-face{font-family:'%s';src:url(data:font/ttf;base64,%s) format('truetype');}"
                % (family, _b64(p))
            )
    return "\n".join(faces)


def build_html():
    """Monta el HTML final con CSS, fuentes y JS embebidos."""
    fonts_css = prepare_assets()
    with open(os.path.join(UI_DIR, "style.css"), "r", encoding="utf-8") as f:
        css = f.read().replace("/*__FONTS__*/", fonts_css)
    with open(os.path.join(UI_DIR, "app.js"), "r", encoding="utf-8") as f:
        js = f.read()
    with open(os.path.join(UI_DIR, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    logo = "data:image/png;base64," + _b64(LOGO_PATH) if os.path.exists(LOGO_PATH) else ""
    html = html.replace("__CSS__", css).replace("__JS__", js).replace("__LOGO__", logo)
    return html


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------

def effective_theme(mode):
    if mode != "system":
        return mode
    st = Gtk.Settings.get_default()
    if st is not None and st.props.gtk_application_prefer_dark_theme:
        return "dark"
    return "light"


class App:
    def __init__(self):
        self.prefs = Prefs()
        self.db = self._build_db()
        self.version = self.prefs.get("version", "nvi")
        self.book = int(self.prefs.get("book", 1))
        self.chapter = int(self.prefs.get("chapter", 1))
        self.verse = int(self.prefs.get("verse", 1))
        self.text_size = int(self.prefs.get("text_size", 19))
        self.verse_font = self.prefs.get("verse_font", "default")
        self.theme = self.prefs.get("theme", "system")
        self.book_map = {b["id"]: b["name"] for b in self.db.books()}
        self.chapter_cache = None

    def _build_db(self):
        bib_path = os.path.join(BASE_DIR, DB_FILENAME)
        if not os.path.exists(bib_path):
            bib_path = db_user_path()
        if os.path.exists(bib_path) and not os.path.exists(db_user_path()):
            try:
                shutil.copy(bib_path, db_user_path())
            except Exception:
                pass
        cur = db_user_path() if os.path.exists(db_user_path()) else bib_path
        return BibleDB(cur)

    # ---------------------------------------------------------------- datos
    def _chapter(self):
        maxch = self.db.chapters(self.version, self.book)
        if maxch == 0:
            maxch = 1
        self.chapter = max(1, min(self.chapter, maxch))
        rows = self.db.verses(self.version, self.book, self.chapter)
        verses = []
        for r in rows:
            num = r["verse"]
            hl = self.db.get_highlight(self.version, self.book, self.chapter, num)
            note = self.db.get_note(self.version, self.book, self.chapter, num)
            if not note:
                note = r.get("notes") or None
            verses.append({
                "num": num,
                "text": r["text"] or "",
                "hl": hl,
                "note": note,
                "marked": self.db.is_bookmarked(self.version, self.book, self.chapter, num),
                "ref": self._ref(num),
            })
        maxv = max((v["verse"] for v in rows), default=1)
        self.verse = min(max(1, self.verse), maxv)
        self.prefs.set("book", self.book)
        self.prefs.set("chapter", self.chapter)
        self.prefs.set("verse", self.verse)
        self.chapter_cache = {
            "book": self.book,
            "bookName": self.book_map.get(self.book, ""),
            "chapter": self.chapter,
            "maxChapter": maxch,
            "versionLabel": dict(VERSIONS).get(self.version, self.version),
            "ref": self._ref(self.verse),
            "verses": verses,
        }
        return self.chapter_cache

    def _ref(self, verse=None):
        v = verse if verse is not None else self.verse
        abbr = ABBR.get(self.book, str(self.book))
        return "%s %s:%s" % (abbr, self.chapter, v)

    def _books(self):
        out = []
        for b in self.db.books():
            out.append({
                "id": b["id"],
                "name": b["name"],
                "abbr": ABBR.get(b["id"], str(b["id"])),
                "testament": b["testament"],
            })
        return out

    def _bookmarks(self):
        out = []
        for b in self.db.bookmarks(self.version):
            out.append({
                "book": b["book_id"],
                "chapter": b["chapter"],
                "verse": b["verse"],
                "ref": "%s %s:%s" % (
                    ABBR.get(b["book_id"], str(b["book_id"])), b["chapter"], b["verse"]),
                "name": b["name"],
            })
        return out

    # ---------------------------------------------------------------- bridge
    def run(self):
        win = Gtk.Window(title=APP_NAME)
        win.set_default_size(1320, 860)
        win.set_resizable(True)
        try:
            if os.path.exists(LOGO_PATH):
                win.set_icon_from_file(LOGO_PATH)
        except Exception:
            pass
        self.win = win

        # Cabecera (min/max/cerrar en la esquina)
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("")
        header.set_subtitle("RV1960 · NTV · NVI · PDT")
        win.set_titlebar(header)

        fs_btn = Gtk.Button(label="⛶")
        fs_btn.set_tooltip_text("Pantalla completa (F11)")
        fs_btn.connect("clicked", lambda w: self._toggle_fullscreen())
        header.pack_end(fs_btn)

        win.connect("destroy", Gtk.main_quit)
        win.connect("key-press-event", self._on_key)

        # WebKit
        self.ucm = WebKit2.UserContentManager()
        self.ucm.register_script_message_handler("biblia")
        self.ucm.connect("script-message-received::biblia", self._on_message)
        self.webview = WebKit2.WebView.new_with_user_content_manager(self.ucm)
        settings = self.webview.get_settings()
        settings.props.enable_javascript = True
        settings.props.enable_smooth_scrolling = True
        try:
            self.webview.set_background_color(Gdk.RGBA(0.96, 0.95, 0.99, 1.0))
        except Exception:
            pass

        win.add(self.webview)
        win.show_all()
        win.maximize()

        try:
            self.webview.load_html(build_html(), "file://" + BASE_DIR + "/")
        except Exception as e:
            print("ERROR cargando la interfaz:", e)

    def _toggle_fullscreen(self):
        if self.win.is_fullscreen():
            self.win.unfullscreen()
        else:
            self.win.fullscreen()

    def _on_key(self, w, ev):
        if ev.keyval == Gdk.KEY_F11:
            self._toggle_fullscreen()
            return True
        return False

    def _on_message(self, manager, js_result):
        try:
            raw = js_result.get_js_value().to_string()
        except Exception:
            return
        try:
            msg = json.loads(raw)
        except Exception:
            return
        mid = msg.get("id")
        action = msg.get("action")
        payload = msg.get("payload") or {}
        self._handle(mid, action, payload)

    def _reply(self, mid, data=None):
        if data is None:
            data = {}
        code = "window.__reply(%d, %s);" % (int(mid), json.dumps(data, ensure_ascii=False))
        GLib.idle_add(self._run_js_once, code)

    def _run_js_once(self, code):
        self.run_js(code)
        return False

    def run_js(self, code):
        try:
            self.webview.evaluate_javascript(code, -1, None, None, None, None, None)
        except Exception:
            pass

    def _handle(self, mid, action, p):
        if action == "init":
            self._reply(mid, {
                "versions": [{"code": c, "label": l} for c, l in VERSIONS],
                "version": self.version,
                "books": self._books(),
                "bookmarks": self._bookmarks(),
                "chapter": self._chapter(),
                "theme": effective_theme(self.theme),
                "themeMode": self.theme,
                "size": self.text_size,
                "verseFont": {"id": self.verse_font, "css": VERSE_FONTS.get(self.verse_font, VERSE_FONTS["default"])},
            })
        elif action == "set_version":
            code = p.get("code")
            if code and code in dict(VERSIONS):
                self.version = code
                self.prefs.set("version", code)
                self.verse = 1
            self._reply(mid, {"chapter": self._chapter(), "bookmarks": self._bookmarks()})
        elif action == "select_book":
            b = int(p.get("id", 0))
            if b and b in self.book_map:
                self.book = b
                self.chapter = 1
                self.verse = 1
            self._reply(mid, {"chapter": self._chapter()})
        elif action == "previous":
            if self.chapter > 1:
                self.chapter -= 1
                self.verse = 1
            self._reply(mid, {"chapter": self._chapter()})
        elif action == "next":
            maxch = self.db.chapters(self.version, self.book)
            if self.chapter < maxch:
                self.chapter += 1
                self.verse = 1
            self._reply(mid, {"chapter": self._chapter()})
        elif action == "go_ref":
            b = int(p.get("book", self.book))
            c = int(p.get("chapter", self.chapter))
            v = int(p.get("verse", self.verse))
            if b in self.book_map:
                self.book = b
                self.chapter = c
                self.verse = v
            self._reply(mid, {"chapter": self._chapter()})
        elif action == "verse_click":
            self.verse = max(1, int(p.get("verse", self.verse)))
            self.prefs.set("verse", self.verse)
            self._reply(mid)
        elif action == "copy":
            self._clip()
            self._reply(mid)
        elif action == "copy_text":
            clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clip.set_text(p.get("text") or "", -1)
            self._reply(mid)
        elif action == "share":
            self._clip()
            self._open_sticker()
            self._reply(mid)
        elif action == "sticker":
            self._open_sticker()
            self._reply(mid)
        elif action == "highlight":
            color = p.get("color")
            if color:
                self.db.set_highlight(self.version, self.book, self.chapter, self.verse, color)
            else:
                self.db.remove_highlight(self.version, self.book, self.chapter, self.verse)
            self._reply(mid)
        elif action == "get_note":
            note = self.db.get_note(self.version, self.book, self.chapter, self.verse)
            self._reply(mid, {"note": note or ""})
        elif action == "save_note":
            self.db.save_note(
                self.version, self.book, self.chapter, self.verse, p.get("note") or ""
            )
            self._reply(mid)
        elif action == "toggle_bookmark":
            active = self.db.toggle_bookmark(
                self.version, self.book, self.chapter, self.verse
            )
            self._reply(mid, {"active": active, "bookmarks": self._bookmarks()})
        elif action == "search":
            term = (p.get("term") or "").strip()
            results = []
            if len(term) >= 3:
                for r in self.db.search(self.version, term):
                    results.append({
                        "ref": "%s %s:%s" % (
                            ABBR.get(r["book_id"], str(r["book_id"])), r["chapter"], r["verse"]),
                        "text": r["text"],
                        "book": r["book_id"],
                        "chapter": r["chapter"],
                        "verse": r["verse"],
                    })
            self._reply(mid, {"results": results})
        elif action == "theme":
            mode = p.get("mode")
            if mode in ("system", "light", "dark"):
                self.theme = mode
                self.prefs.set("theme", mode)
            self._reply(mid)
        elif action == "font_size":
            self.text_size = max(13, min(34, int(p.get("size", self.text_size))))
            self.prefs.set("text_size", self.text_size)
            self._reply(mid)
        elif action == "verse_font":
            f = p.get("font")
            if f in VERSE_FONTS:
                self.verse_font = f
                self.prefs.set("verse_font", f)
            self._reply(mid)

    def _clip(self):
        rows = self.db.verses(self.version, self.book, self.chapter)
        vs = next((v for v in rows if v["verse"] == self.verse), None)
        ref = "%s (%s)" % (self._ref(), dict(VERSIONS).get(self.version, self.version))
        txt = vs["text"] if vs else ""
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clip.set_text("%s\n\n%s" % (ref, txt), -1)

    def _open_sticker(self):
        rows = self.db.verses(self.version, self.book, self.chapter)
        vs = next((v for v in rows if v["verse"] == self.verse), None)
        text = vs["text"] if vs else ""
        StickerWindow(
            self.win, self.db, self.version, self.book, self.chapter, self.verse, text
        ).show_all()


def main():
    app = App()
    app.run()
    Gtk.main()


if __name__ == "__main__":
    main()