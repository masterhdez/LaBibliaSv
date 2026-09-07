#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publica "La Biblia Sv" en GitHub: crea el repositorio, sube el proyecto,
crea el release v1.0.0 con el .deb y activa GitHub Pages (docs/).

Uso:
    GH_TOKEN=tu_pat python3 publicar_github.py
"""
import base64
import json
import os
import sys
import time

import requests

OWNER = "masterhdez"
REPO = "LaBibliaSv"
DEB = "/home/master/Escritorio/LaBibliaSv/dist/la-biblia-sv_1.0.0_amd64.deb"
ROOT = "/home/master/Escritorio/LaBibliaSv"
VERSION_TAG = "v1.0.0"
VERSION_NAME = "1.0.0"

SKIP_DIRS = {"dist", "__pycache__", ".git", "docs_src"}
SKIP_EXTS = {".pyc", ".log", ".xwd", ".deb"}

API = "https://api.github.com"
HDRS = {
    "Authorization": "Bearer " + os.environ.get("GH_TOKEN", ""),
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def gh(method, url, **kw):
    kw.setdefault("headers", HDRS)
    r = requests.request(method, url, **kw)
    if r.status_code >= 400:
        raise RuntimeError("%s %s -> %s %s" % (method, url, r.status_code, r.text[:400]))
    return r.json()

def upload_url():
    return "https://github.com/%s/%s/releases/latest/download/la-biblia-sv_1.0.0_amd64.deb" % (OWNER, REPO)

def walk():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SKIP_EXTS or fn.startswith("."):
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, ROOT)
            files.append((rel, fp))
    return files

def main():
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        sys.exit("Falta GH_TOKEN (Personal Access Token) en el entorno.")
    me = gh("GET", API + "/user")
    print("Autenticado como:", me.get("login"), me.get("html_url"))

    # 1. Repositorio
    repo_url = API + "/repos/%s/%s" % (OWNER, REPO)
    try:
        repo = gh("GET", repo_url)
        print("Repo ya existe:", repo["html_url"])
    except RuntimeError as e:
        gh("POST", API + "/user/repos", json={
            "name": REPO,
            "description": "La Biblia Sv — Lector de la Biblia para Linux (Mint / Ubuntu / Debian). RV1960, NTV, NVI, PDT.",
            "homepage": "https://%s.github.io/%s/" % (OWNER, REPO),
            "auto_init": True,
            "private": False,
        })
        repo = gh("GET", repo_url)
        print("Repo creado:", repo["html_url"])

    # 2. Descargar URL real en docs/index.html
    dl = upload_url()
    idx = os.path.join(ROOT, "docs", "index.html")
    with open(idx, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__DOWNLOAD_URL__", dl)
    with open(idx, "w", encoding="utf-8") as f:
        f.write(html)
    print("Download URL:", dl)

    # 3. Subir archivos (Contents API; actualiza sobre SHA si ya existe)
    def sha_of(path):
        try:
            return gh("GET", repo_url + "/contents/" + path)["sha"]
        except RuntimeError:
            return None

    files = walk()
    # docs/ también se sube (es la fuente de GitHub Pages)
    for rel, fp in files:
        path = rel.replace(os.sep, "/")
        with open(fp, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        data = {"message": "sube " + path, "content": b64}
        s = sha_of(path)
        if s:
            data["sha"] = s
        try:
            gh("PUT", repo_url + "/contents/" + path, json=data)
            print("  subido", path)
        except RuntimeError as e:
            print("  ERROR", path, str(e)[:200])

    # 4. Release v1.0.0 con el .deb
    body = (
        "## La Biblia Sv 1.0.0\n\n"
        "Lector de la Biblia para **Linux Mint / Ubuntu / Debian** con interfaz "
        "Material Design (RV1960 · NTV · NVI · PDT).\n\n"
        "### Instalar\n```bash\nsudo apt install ./la-biblia-sv_1.0.0_amd64.deb\n```\n\n"
        "### Novedades\n"
        "- Ventana normal redimensionable con minimizar/maximizar/cerrar.\n"
        "- UI Material Design (WebKit2): sombras, ripples, animaciones, modo oscuro e iconos Font Awesome.\n"
        "- 4 versiones, búsqueda, resaltados, notas, marcadores, copiar/compartir versículos.\n"
        "- Ajustes (versión, tema, tamaño) y letra del versículo (6 tipografías).\n"
        "- Generador de stickers: color, imagen de fondo, letra de carta, PNG.\n"
        "- Powered by Agdala 2026.\n"
    )
    try:
        release = gh("GET", repo_url + "/releases/tags/" + VERSION_TAG)
        print("Release ya existe:", release["html_url"])
    except RuntimeError:
        release = gh("POST", repo_url + "/releases", json={
            "tag_name": VERSION_TAG,
            "target_commitish": "main",
            "name": "La Biblia Sv " + VERSION_NAME,
            "body": body,
            "draft": False,
            "prerelease": False,
        })
        print("Release creado:", release["html_url"])

    upload_url_tpl = release["upload_url"].split("{")[0]
    with open(DEB, "rb") as f:
        deb_data = f.read()
    r = requests.post(
        upload_url_tpl,
        headers={**HDRS, "Content-Type": "application/vnd.debian.binary-package"},
        params={"name": os.path.basename(DEB), "label": "La Biblia Sv .deb"},
        data=deb_data,
    )
    if r.status_code >= 400:
        # asset ya subido
        assets = gh("GET", release["url"] + "/assets")
        found = any(a["name"] == os.path.basename(DEB) for a in assets)
        if not found:
            raise RuntimeError("Subir asset falló: %s %s" % (r.status_code, r.text[:300]))
    else:
        print("Asset subido:", r.json()["browser_download_url"])

    # 5. GitHub Pages (rama main, carpeta /docs)
    try:
        gh("POST", API + "/repos/%s/%s/pages" % (OWNER, REPO), json={
            "source": {"branch": "main", "path": "/docs"},
        })
        print("GitHub Pages configurado...")
    except RuntimeError as e:
        print("Pages ya configuradas:", str(e)[:160])

    print("\nTodo listo:")
    print("  Repositorio:", repo["html_url"])
    print("  Página web: https://%s.github.io/%s/" % (OWNER, REPO))
    print("  Descarga  :", dl)

if __name__ == "__main__":
    main()