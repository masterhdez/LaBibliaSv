/* La Biblia Sv — UI (WebKit2). Puente con Python vía messageHandlers.biblia */
"use strict";

window.__seq = 0;
window.__cbs = {};

function api(action, payload, cb) {
  var id = ++window.__seq;
  if (cb) window.__cbs[id] = cb;
  window.webkit.messageHandlers.biblia.postMessage(JSON.stringify({ id: id, action: action, payload: payload || {} }));
}
window.__reply = function (id, data) {
  var cb = window.__cbs[id];
  delete window.__cbs[id];
  if (cb) cb(data);
};

var IC = {
  search: "\uf002", copy: "\uf0c5", share: "\uf1e0", book: "\uf02d",
  bookmark: "\uf02e", pencil: "\uf303", highlighter: "\uf591",
  trash: "\uf2ed", left: "\uf053", right: "\uf054", close: "\uf00d",
  note: "\uf249", sticker: "\uf03e", moon: "\uf186", sun: "\uf185",
  bookmarksTab: "\uf15b", font: "\uf031", minus: "\uf068", plus: "\uf067",
  check: "\uf00c", flag: "\uf111", searchX: "\uf00d",
  palette: "\uf1fc", image: "\uf03e", gear: "\uf013",
};
function I(name) { return '<i class="fa">' + IC[name] + "</i>"; }

var D = {};
var curVerse = 1;
var actShown = false;
var themeMode = "system";

function $(id) { return document.getElementById(id); }
function el(tag, cls, html) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* ---------------- Ripple ---------------- */
function ripple(e) {
  var t = e.currentTarget, r = t.getBoundingClientRect();
  var s = Math.max(r.width, r.height);
  var ink = el("span", "ripple-ink");
  ink.style.width = ink.style.height = s + "px";
  ink.style.left = (e.clientX - r.left - s / 2) + "px";
  ink.style.top = (e.clientY - r.top - s / 2) + "px";
  t.appendChild(ink);
  requestAnimationFrame(function () { ink.classList.add("zoom"); });
  setTimeout(function () { ink.remove(); }, 600);
}
["card", "navbtn", "tool", "abtn", "tab", "font-card", "swatch", "result", "mclose", "btn"].forEach(function (c) {
  document.addEventListener("click", function (e) {
    var node = e.target.closest("." + c);
    if (node && node.getAttribute("data-noripple") === null) ripple(e);
  });
});

/* ---------------- Snackbar ---------------- */
var snackTimer = null;
function snack(msg) {
  var s = $("snack");
  s.textContent = msg;
  s.classList.add("show");
  clearTimeout(snackTimer);
  snackTimer = setTimeout(function () { s.classList.remove("show"); }, 2100);
}

/* ---------------- Theme / size / font ---------------- */
function preloadFonts() {
  ["\"LBS GreatVibes\"", "\"LBS Dancing\"", "\"LBS Caveat\"", "\"LBS Playfair\"", "\"LBS Oswald\""].forEach(function (f) {
    try { document.fonts.load("24px " + f, "Alfa y Omega"); } catch (e) {}
  });
}
function applyTheme(mode) {
  var dark = mode === "dark" || (mode === "system" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.body.classList.toggle("dark", dark);
  $("btnTheme").innerHTML = dark ? I("sun") : I("moon");
}
function setSize(n) {
  n = Math.max(13, Math.min(34, n));
  document.documentElement.style.setProperty("--vs", n + "px");
  $("sizeNum").textContent = n;
  api("font_size", { size: n });
}
function setVerseFont(f) {
  document.documentElement.style.setProperty("--vf", f.css);
  document.querySelectorAll(".font-card").forEach(function (c) {
    c.classList.toggle("sel", c.getAttribute("data-font") === f.id);
  });
  api("verse_font", { font: f.id });
}

/* ---------------- Settings ---------------- */
function copyText(text, msg) {
  api("copy_text", { text: text });
  snack(msg || "Copiado al portapapeles");
}
function setThemeMode(mode) {
  themeMode = mode;
  applyTheme(mode);
  api("theme", { mode: mode });
  document.querySelectorAll("#setTheme .seg-btn").forEach(function (b) {
    b.classList.toggle("active", b.getAttribute("data-theme") === mode);
  });
}
function renderSettings() {
  var sel = D.version;
  var sv = $("setVersions");
  sv.innerHTML = "";
  (D.versions || []).forEach(function (v) {
    var r = el("button", "opt-row" + (v.code === sel ? " sel" : ""), "");
    r.setAttribute("data-noripple", "");
    r.innerHTML = '<span class="opt-name">' + esc(v.label) + "</span>" +
      (v.code === sel ? '<span class="opt-check">' + I("check") + "</span>" : "");
    r.addEventListener("click", function () {
      api("set_version", { code: v.code }, function (d) {
        D.version = v.code;
        curVerse = 1;
        D.bookmarks = d.bookmarks;
        renderBookmarks();
        renderChapter(d.chapter);
        renderSettings();
        snack("Versión: " + v.label);
      });
    });
    sv.appendChild(r);
  });
  document.querySelectorAll("#setTheme .seg-btn").forEach(function (b) {
    b.classList.toggle("active", b.getAttribute("data-theme") === themeMode);
  });
  var sz = parseInt($("sizeNum").textContent, 10);
  $("setSizeSlider").value = sz;
  $("setSizeVal").textContent = sz;
}
function openSettings() {
  renderSettings();
  openModal("settingsModal");
}

/* ---------------- Books & bookmarks ---------------- */
function renderBooks() {
  var box = $("books");
  box.innerHTML = "";
  ["AT", "NT"].forEach(function (t) {
    box.appendChild(el("div", "group-label", t === "AT" ? "Antiguo Testamento" : "Nuevo Testamento"));
    D.books.forEach(function (b, i) {
      if (b.testament !== t) return;
      var c = el("div", "card book" + (b.id === D.book ? " active" : ""), "");
      c.setAttribute("data-id", b.id);
      c.setAttribute("data-noripple", "");
      var main = el("span", "card-main", "");
      main.innerHTML = esc(b.name) + '<span class="abbr">' + esc(b.abbr) + "</span>";
      c.appendChild(main);
      c.addEventListener("click", function () {
        api("select_book", { id: b.id }, function (d) {
          curVerse = 1;
          renderChapter(d.chapter);
        });
      });
      box.appendChild(c);
    });
  });
}
function renderBookmarks() {
  var box = $("marks");
  box.innerHTML = "";
  if (!D.bookmarks || D.bookmarks.length === 0) {
    box.appendChild(el("div", "empty", I("bookmark") + "Aún no hay marcadores"));
    return;
  }
  D.bookmarks.forEach(function (m) {
    var c = el("div", "card", "");
    c.setAttribute("data-noripple", "");
    var main = el("span", "card-main", "");
    main.innerHTML = '<span class="abbr">' + esc(m.ref) + "</span>";
    c.appendChild(main);
    c.appendChild(el("div", "card-sub", esc(m.name)));
c.addEventListener("click", function () {
        api("go_ref", { book: m.book, chapter: m.chapter, verse: m.verse }, function (d) {
          curVerse = m.verse;
          renderChapter(d.chapter);
        });
      });
    box.appendChild(c);
  });
}

/* ---------------- Chapter ---------------- */
function renderChapter(c) {
  D.book = c.book; D.chapter = c.chapter; D.maxChapter = c.maxChapter;
  D.verses = c.verses;
  $("bookTitle").textContent = c.bookName;
  $("chapterLabel").textContent = "Capítulo " + c.chapter + " de " + c.maxChapter + " · " + c.versionLabel;
  var box = $("scroll");
  var card = el("div", "chapter-card", "");
  var head = el("div", "chapter-header", "");
  var big = el("div", "big", "");
  big.appendChild(el("span", "fa", IC.book));
  head.appendChild(big);
  head.appendChild(el("div", "nm", esc(c.bookName) + '<span class="sub">Capítulo ' + c.chapter + "</span>"));
  card.appendChild(head);
  var changed = !D._lastRef || D._lastRef !== c.ref;
  D._lastRef = c.ref;
  c.verses.forEach(function (v, i) {
    var node = el("div", "verse" + (v.hl ? " hl-" + v.hl : ""), "");
    node.setAttribute("data-v", v.num);
    node.setAttribute("data-noripple", "");
    var vn = el("span", "vnum", v.num);
    var vt = el("span", "vtext", esc(v.text));
    vt.innerHTML = esc(v.text);
    node.appendChild(vn);
    node.appendChild(vt);
    if (v.note) node.appendChild(el("span", "vnote", I("note")));
    appendRippleTarget(node);
    node.addEventListener("click", function (ev) { selectVerse(v.num, ev); });
    if (changed) node.classList.add("vrow-appear");
    card.appendChild(node);
  });
  box.innerHTML = "";
  box.appendChild(card);
  document.querySelectorAll(".book.active").forEach(function (b) { b.classList.remove("active"); });
  var ab = document.querySelector('.book[data-id="' + c.book + '"]');
  if (ab) ab.classList.add("active");
  if (D.bookmarks) renderBookmarks();
  setTimeout(function () {
    var sel = box.querySelector('.verse[data-v="' + curVerse + '"]');
    if (sel) sel.scrollIntoView({ block: "center", behavior: "auto" });
  }, 40);
}
function appendRippleTarget(node) {
  var t = el("span", "ripple-ink");
  t.style.display = "none";
  node.appendChild(t);
}

/* verse click -> selection + actions bar */
function selectVerse(v, ev) {
  var elOld = document.querySelector('.verse.sel[data-v="' + curVerse + '"]');
  if (elOld) elOld.classList.remove("sel");
  curVerse = v;
  var node = document.querySelector('.verse[data-v="' + v + '"]');
  if (node) node.classList.add("sel");
  var noteMarked = !!node.querySelector(".vnote");
  $("actRef").textContent = D.verses ? D.verses.find(function (x) { return x.num === v; }).ref : "";
  $("btnMark").classList.toggle("active", D.verses && D.verses.find(function (x) { return x.num === v; }).marked);
  $("btnNote").classList.toggle("active", noteMarked);
  $("btnClear").style.display = D.verses && D.verses.find(function (x) { return x.num === v; }).hl ? "" : "none";
  showActions(true);
  api("verse_click", { verse: v });
}
function showActions(on) {
  $("actions").classList.toggle("show", !!on);
  actShown = !!on;
}

/* ---------------- Modals ---------------- */
function openModal(id) { $(id).classList.add("show"); }
function closeModal(id) { $(id).classList.remove("show"); }
function bindClose(id) {
  $(id).addEventListener("click", function (e) {
    if (e.target === $(id) || e.target.classList.contains("mclose")) closeModal(id);
  });
}

function currentVerse() {
  return D.verses ? D.verses.find(function (x) { return x.num === curVerse; }) : null;
}

function openHighlight() {
  var cv = currentVerse();
  document.querySelectorAll("#hlPalette .swatch").forEach(function (s) {
    s.classList.toggle("sel", s.getAttribute("data-hl") === (cv && cv.hl));
  });
  openModal("hlModal");
}
function setHighlight(color) {
  api("highlight", { color: color }, function (d) {
    var cv = currentVerse();
    if (cv) {
      cv.hl = color;
      var node = document.querySelector('.verse[data-v="' + cv.num + '"]');
      node.className = "verse" + (color ? " hl-" + color : "");
      node.querySelector(".vnum").classList.remove("ripple-ink");
    }
    $("btnClear").style.display = color ? "" : "none";
    closeModal("hlModal");
    snack(color ? "Versículo resaltado" : "Resaltado eliminado");
  });
}

function openNote() {
  api("get_note", {}, function (d) {
    $("noteField").value = d.note || "";
    openModal("noteModal");
    $("noteField").focus();
  });
}
function saveNote() {
  api("save_note", { note: $("noteField").value }, function () {
    var cv = currentVerse(); if (!cv) return;
    cv.note = $("noteField").value.trim();
    var node = document.querySelector('.verse[data-v="' + cv.num + '"]');
    var badge = node.querySelector(".vnote");
    if (cv.note && !badge) node.appendChild(el("span", "vnote", I("note")));
    else if (!cv.note && badge) badge.remove();
    closeModal("noteModal");
    snack("Nota guardada");
  });
}

function openSearch() {
  $("searchInput").value = "";
  $("searchResults").innerHTML = '<div class="empty">' + I("search") + "Escribe 3+ letras para buscar</div>";
  $("searchInput").focus();
  openModal("searchModal");
}
function doSearch() {
  var term = $("searchInput").value.trim();
  if (term.length < 3) return;
  var res = $("searchResults");
  res.innerHTML = '<div class="empty">' + I("search") + "Buscando…</div>";
  api("search", { term: term }, function (d) {
    res.innerHTML = "";
    if (!d.results || d.results.length === 0) {
      res.appendChild(el("div", "empty", I("searchX") + "Sin resultados para «" + esc(term) + "»"));
      return;
    }
    d.results.forEach(function (r) {
      var b = el("button", "result", "");
      b.setAttribute("data-noripple", "");
      b.innerHTML = '<div class="r1">' + esc(r.ref) + "</div><div class='r2'>" + esc(r.text) + "</div>";
      b.addEventListener("click", function () {
        closeModal("searchModal");
        api("go_ref", { book: r.book, chapter: r.chapter, verse: r.verse }, function (d) {
          curVerse = r.verse;
          renderChapter(d.chapter);
        });
      });
      res.appendChild(b);
    });
    snack(d.results.length + " resultado(s)");
  });
}

function openFonts() {
  openModal("fontModal");
}

function toggleTheme() {
  var dk = document.body.classList.contains("dark");
  setThemeMode(dk ? "light" : "dark");
}

function toggleMark() {
  api("toggle_bookmark", {}, function (d) {
    $("btnMark").classList.toggle("active", d.active);
    if (d.bookmarks) D.bookmarks = d.bookmarks;
    renderBookmarks();
    snack(d.active ? "Marcador añadido" : "Marcador eliminado");
  });
}

function copyNow() { api("copy", {}); snack("Copiado al portapapeles"); }
function shareNow() { api("share", {}); }
function stickerNow() { api("sticker", {}); }
function clearHighlight() { setHighlight(null); }

/* ---------------- Tabs ---------------- */
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(function (t) {
    t.classList.toggle("active", t.getAttribute("data-tab") === name);
  });
  document.querySelectorAll(".panel").forEach(function (p) {
    p.classList.toggle("active", p.id === name);
  });
}

/* ---------------- Init ---------------- */
function boot() {
  api("init", {}, function (d) {
    D.version = d.version;
    D.versions = d.versions;
    D.books = d.books;
    D.bookmarks = d.bookmarks;
    themeMode = d.themeMode || "system";
    curVerse = d.chapter.verse || 1;
    applyTheme(d.theme);
    setSize(d.size);
    preloadFonts();
    setVerseFont({ id: d.verseFont.id, css: d.verseFont.css });
    renderBooks();
    renderBookmarks();
    renderChapter(d.chapter);
    var sel = $("versionSel");
    sel.innerHTML = "";
    d.versions.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v.code; o.textContent = v.label; sel.appendChild(o);
    });
    sel.value = d.version;
    sel.addEventListener("change", function () {
      api("set_version", { code: sel.value }, function (d) {
        curVerse = 1;
        D.bookmarks = d.bookmarks;
        renderBookmarks();
        renderChapter(d.chapter);
        snack("Versión: " + sel.options[sel.selectedIndex].textContent);
      });
    });
    snack("Biblia Sv lista");
  });
}

function bootWhenReady(attempt) {
  try {
    if (typeof window.webkit !== "undefined" && window.webkit.messageHandlers && window.webkit.messageHandlers.biblia) {
      boot();
      return;
    }
  } catch (e) {}
  if ((attempt || 0) < 80) setTimeout(function () { bootWhenReady((attempt || 0) + 1); }, 200);
}

/* ---------------- Wiring ---------------- */
document.addEventListener("DOMContentLoaded", function () {
  var nav = function (action) {
    api(action, {}, function (d) {
      curVerse = 1;
      renderChapter(d.chapter);
    });
  };
  $("prevB").addEventListener("click", function () { nav("previous"); });
  $("nextB").addEventListener("click", function () { nav("next"); });
  $("fab").addEventListener("click", openSearch);
  $("btnSearch").addEventListener("click", openSearch);
  $("btnSettings").addEventListener("click", openSettings);
  $("btnFont").addEventListener("click", openFonts);
  $("btnSticker").addEventListener("click", stickerNow);
  $("btnTheme").addEventListener("click", toggleTheme);
  $("sizeMinus").addEventListener("click", function () { setSize(parseInt($("sizeNum").textContent, 10) - 1); });
  $("sizePlus").addEventListener("click", function () { setSize(parseInt($("sizeNum").textContent, 10) + 1); });

  ["hlModal", "searchModal", "noteModal", "fontModal", "settingsModal"].forEach(bindClose);
  $("searchDone").addEventListener("click", doSearch);
  $("searchInput").addEventListener("keydown", function (e) { if (e.key === "Enter") doSearch(); });
  $("noteSave").addEventListener("click", saveNote);

  document.querySelectorAll("#hlPalette .swatch").forEach(function (s) {
    s.addEventListener("click", function () {
      var c = s.getAttribute("data-hl");
      setHighlight(c === "none" ? null : c);
    });
  });
  document.querySelectorAll(".font-card").forEach(function (c) {
    c.addEventListener("click", function () {
      setVerseFont({ id: c.getAttribute("data-font"), css: c.getAttribute("data-css") });
    });
  });

  document.querySelectorAll(".tab").forEach(function (t) {
    t.addEventListener("click", function () { switchTab(t.getAttribute("data-tab")); });
  });

  document.querySelectorAll(".abtn").forEach(function (b) {
    b.setAttribute("data-noripple", "");
  });
  document.querySelectorAll("#setTheme .seg-btn").forEach(function (b) {
    b.addEventListener("click", function () { setThemeMode(b.getAttribute("data-theme")); });
  });
  $("setSizeSlider").addEventListener("input", function () {
    setSize(parseInt(this.value, 10));
    $("setSizeVal").textContent = this.value;
  });
  document.addEventListener("click", function (e) {
    var chip = e.target.closest(".copy-chip");
    if (chip && chip.getAttribute("data-copy")) {
      copyText(chip.getAttribute("data-copy"));
    }
  });
  $("btnCopy").addEventListener("click", copyNow);
  $("btnShare").addEventListener("click", shareNow);
  $("btnHl").addEventListener("click", openHighlight);
  $("btnNote").addEventListener("click", openNote);
  $("btnMark").addEventListener("click", toggleMark);
  $("btnClear").addEventListener("click", clearHighlight);

  // Esconder la barra de acciones al hacer scroll lejos (con toque en el vacío)
  document.body.addEventListener("click", function (e) {
    if (!e.target.closest(".verse") && !e.target.closest("#actions")) showActions(false);
  });

  bootWhenReady();
});