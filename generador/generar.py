#!/usr/bin/env python3
"""
Genera el README del perfil y todos sus SVG, en claro y en oscuro.

Dirección visual: la de Motorflux «Vidrio» (29/10/2026). Fondo claro con focos de luz azul y
turquesa, una sola tipografía (Inter) con interletraje negativo en lo grande, y vidrio solo donde
significa algo: la cápsula del banner es vidrio de verdad (refracta lo que tiene detrás) y las
tarjetas son vidrio «quieto» (relleno translúcido y canto iluminado).

Por qué todo está en trazados: GitHub enseña los SVG del README como <img>, y así el navegador no
carga fuentes externas. El texto se convierte aquí en trazados de Inter (con su interletraje y su
kerning), de modo que se ve igual en cualquier navegador y no depende de nada.

Uso:  pip install fonttools brotli uharfbuzz
      python generador/generar.py
Todo lo que se cambia a mano (textos, enlaces, tecnologías) está en CONTENIDO, más abajo.
"""
from __future__ import annotations

import base64
import io
import re
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
ASSETS = REPO / "assets"
USUARIO = "eriizzo"

# ══════════════════════════════════════════════════════════════════════════════════════════════
#  CONTENIDO
# ══════════════════════════════════════════════════════════════════════════════════════════════
CONTENIDO = {
    "nombre": "Erizo",
    "saludo": "Hola, soy",
    "lema": ("Sistemas, ", "ciberseguridad e IA", "."),  # la parte del medio lleva el brillo
    "capsula": [
        ("maletin", "Administrador de sistemas en Daumar"),
        ("escudo", "Máster en ciberseguridad"),
    ],
    "linkedin": "https://www.linkedin.com/in/eriicperezz/",
    "instagram": "https://www.instagram.com/eriicpeerezz_/",
    "sobre_mi": [
        "Me encanta la informática, sobre todo la <b>ciberseguridad</b> y la <b>inteligencia artificial</b>.",
        "Trabajo como <b>administrador de sistemas en Daumar</b> y estudio un <b>máster en ciberseguridad</b>.",
        "Soy técnico superior en <b>ASIR</b> y hablo castellano, catalán e inglés.",
    ],
    "proyectos": [
        {
            "id": "motorflux",
            "nombre": "Motorflux",
            "texto": "Software para concesionarios de ocasión: stock, OCR con IA y contratos.",
            "chips": ["SaaS", "IA", "Node.js", "PostgreSQL"],
            "enlace": "https://motorflux.es",
            "etiqueta": "motorflux.es",
            "icono": "motorflux",
            "luz": ("a", 0.86, 0.06),
        },
        {
            "id": "bella",
            "nombre": "Bel·la",
            "texto": "Web de un centro de estética especializado en uñas, con reserva de cita.",
            "chips": ["Diseño web", "HTML y CSS", "JavaScript"],
            "enlace": "https://bellastudio.es/",
            "etiqueta": "bellastudio.es",
            "icono": "bella",
            "luz": ("b", 0.14, 0.04),
        },
        {
            "id": "erizocoach",
            "nombre": "Erizo Coach",
            "texto": "Asistente de League of Legends: runas y build al elegir, y qué comprar.",
            "chips": ["Python", "API de Riot", "Windows"],
            "enlace": f"https://github.com/{USUARIO}/ErizoCoach",
            "etiqueta": "Ver código",
            "icono": "erizocoach",
            "luz": ("b", 0.90, 0.96),
        },
    ],
    "tecnologias": [
        ("Sistemas", ["Linux", "Docker", "Traefik", "Nginx", "Raspberry Pi"]),
        ("Seguridad", ["Redes", "Hardening", "Despliegue seguro", "Auditoría web"]),
        ("Desarrollo", ["Python", "JavaScript", "Node.js", "Astro", "React", "PHP"]),
        ("Datos e IA", ["PostgreSQL", "MariaDB", "n8n", "OCR con IA"]),
    ],
}

# ══════════════════════════════════════════════════════════════════════════════════════════════
#  PALETA  (los valores de Motorflux «Vidrio», web pública: claro por defecto y «azul noche»)
# ══════════════════════════════════════════════════════════════════════════════════════════════
TEMAS = {
    "claro": {
        "fondo": "#F5F7FB", "texto": "#0B1A2E", "texto2": "#3D4C61",
        "acento": "#0752BA", "intenso": "#0A5FD1", "sobre": "#0B1A2E",
        "luz_a": "#5AA9FF", "luz_b": "#7FE3D8", "fuerza_hero": 0.40, "fuerza": 0.34,
        "vidrio_alto": 0.74, "vidrio_bajo": 0.56, "vidrio_color": "#FFFFFF",
        "tarjeta_alto": 0.62, "tarjeta_bajo": 0.46, "luz_tarjeta": (1.5, 0.8),
        "chip_texto": "#3D4C61", "enlace": "#0752BA", "tinte_enlace": 0.10, "mezcla_brillo": 0.6,
        "flotante": ("#FFFFFF", 0.48), "canto": 1.0, "borde": ("#FFFFFF", 0.80),
        "anillo": ("#0B1A2E", 0.07), "sombra": ("#0B1A2E", 0.28), "puntos": 0.13,
        "brillo": 0.55, "relleno": 0.06, "pagina": "#FFFFFF",
    },
    "oscuro": {
        "fondo": "#0A1426", "texto": "#EEF3FA", "texto2": "#A7B6CB",
        "acento": "#6AAEFF", "intenso": "#0A5FD1", "sobre": "#EEF3FA",
        "luz_a": "#5AA9FF", "luz_b": "#7FE3D8", "fuerza_hero": 0.30, "fuerza": 0.24,
        "vidrio_alto": 0.09, "vidrio_bajo": 0.04, "vidrio_color": "#FFFFFF",
        # En oscuro el turquesa ilumina mucho: con la luz de las tarjetas al 1,5 el texto secundario
        # bajaba a 2,8:1 en el centro del foco. Con estos valores el peor caso pasa de 4,5:1.
        "tarjeta_alto": 0.07, "tarjeta_bajo": 0.03, "luz_tarjeta": (0.75, 0.45),
        "chip_texto": "#CBD5E3", "enlace": "#ACD1FD", "tinte_enlace": 0.16, "mezcla_brillo": 0.8,
        "flotante": ("#0E182A", 0.50), "canto": 0.22, "borde": ("#FFFFFF", 0.10),
        "anillo": ("#FFFFFF", 0.06), "sombra": ("#000000", 0.62), "puntos": 0.12,
        "brillo": 0.16, "relleno": 0.08, "pagina": "#0D1117",
    },
}
CURVA = "cubic-bezier(0.23, 1, 0.32, 1)"


def hexrgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mezcla(a: str, b: str, t: float) -> str:
    """color-mix(in srgb, a t, b): t es la parte de a."""
    ra, ga, ba = hexrgb(a)
    rb, gb, bb = hexrgb(b)
    return "#%02X%02X%02X" % (round(ra * t + rb * (1 - t)), round(ga * t + gb * (1 - t)), round(ba * t + bb * (1 - t)))


def n(v: float, d: int = 2) -> str:
    s = f"{v:.{d}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  TIPOGRAFÍA: Inter variable → trazados con kerning (HarfBuzz) e interletraje
# ══════════════════════════════════════════════════════════════════════════════════════════════
class Tipografia:
    def __init__(self, ruta: Path):
        tt = TTFont(ruta)
        tt.flavor = None
        buf = io.BytesIO()
        tt.save(buf)
        datos = buf.getvalue()
        self.tt = TTFont(io.BytesIO(datos))
        self.upm = self.tt["head"].unitsPerEm
        self.orden = self.tt.getGlyphOrder()
        self.cara = hb.Face(datos)
        self._conjuntos: dict = {}

    @lru_cache(maxsize=None)
    def glifos(self, texto: str, peso: float, opsz: float):
        fuente = hb.Font(self.cara)
        fuente.scale = (self.upm, self.upm)
        fuente.set_variations({"wght": peso, "opsz": opsz})
        buf = hb.Buffer()
        buf.add_str(texto)
        buf.guess_segment_properties()
        hb.shape(fuente, buf, {"kern": True, "liga": True, "calt": True})
        return tuple((i.codepoint, p.x_advance, p.x_offset, p.y_offset)
                     for i, p in zip(buf.glyph_infos, buf.glyph_positions))

    @lru_cache(maxsize=None)
    def contorno(self, gid: int, peso: float, opsz: float) -> str:
        clave = (peso, opsz)
        if clave not in self._conjuntos:
            self._conjuntos[clave] = self.tt.getGlyphSet(location={"wght": peso, "opsz": opsz})
        conjunto = self._conjuntos[clave]
        pluma = SVGPathPen(conjunto, ntos=lambda v: str(round(v)))
        conjunto[self.orden[gid]].draw(pluma)
        return pluma.getCommands()


TIPO = Tipografia(AQUI / "inter" / "inter-latin-opsz-normal.woff2")


def opsz_para(tam: float) -> float:
    return max(14.0, min(32.0, round(tam * 0.72)))


def medir(texto: str, tam: float, peso: float = 500, track: float = 0.0) -> float:
    gl = TIPO.glifos(texto, peso, opsz_para(tam))
    total = sum(g[1] for g in gl) + track * TIPO.upm * (len(gl) - 1)
    return total * tam / TIPO.upm


def partir(texto: str, tam: float, peso: float, ancho: float, track: float = 0.0) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and medir(prueba, tam, peso, track) > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  DOCUMENTO SVG
# ══════════════════════════════════════════════════════════════════════════════════════════════
CSS_BASE = f"""
.deriva-a, .deriva-b, .deriva-c {{ transform-box: fill-box; transform-origin: center; }}
@media (prefers-reduced-motion: no-preference) {{
  .entra {{ animation: entra 1.1s {CURVA} both; }}
  .deriva-a {{ animation: deriva-a 17s ease-in-out infinite alternate; }}
  .deriva-b {{ animation: deriva-b 23s ease-in-out -6s infinite alternate; }}
  .deriva-c {{ animation: deriva-c 29s ease-in-out -11s infinite alternate; }}
}}
@keyframes entra {{ from {{ opacity: 0; transform: translateY(14px); filter: blur(8px); }} to {{ opacity: 1; transform: none; filter: none; }} }}
@keyframes deriva-a {{ from {{ transform: translate(-4%, 0) scale(1); }} to {{ transform: translate(4%, -3%) scale(1.08); }} }}
@keyframes deriva-b {{ from {{ transform: translate(3%, 2%) scale(1.06); }} to {{ transform: translate(-4%, -2%) scale(1); }} }}
@keyframes deriva-c {{ from {{ transform: translate(-3%, 3%) scale(1); }} to {{ transform: translate(3%, -1%) scale(1.07); }} }}
"""


class Documento:
    def __init__(self, ancho: float, alto: float, titulo: str, descripcion: str):
        self.w, self.h = ancho, alto
        self.titulo, self.descripcion = titulo, descripcion
        self.defs: list[str] = []
        self.css: list[str] = [CSS_BASE]
        self.cuerpo: list[str] = []
        self._glifos: dict = {}
        self._n = 0

    def uid(self, base: str) -> str:
        self._n += 1
        return f"{base}{self._n}"

    def _glifo(self, gid: int, peso: float, opsz: float):
        clave = (gid, peso, opsz)
        if clave not in self._glifos:
            d = TIPO.contorno(gid, peso, opsz)
            if d:
                ref = f"g{len(self._glifos)}"
                self.defs.append(f'<path id="{ref}" d="{d}"/>')
                self._glifos[clave] = ref
            else:
                self._glifos[clave] = None
        return self._glifos[clave]

    def texto(self, s: str, x: float, y: float, tam: float, peso: float = 500, track: float = 0.0,
              ancla: str = "start", relleno: str = "currentColor", extra: str = "") -> tuple[str, float]:
        """Devuelve (grupo SVG, ancho). y es la línea base."""
        opsz = opsz_para(tam)
        gl = TIPO.glifos(s, peso, opsz)
        paso = track * TIPO.upm
        total = sum(g[1] for g in gl) + paso * (len(gl) - 1)
        esc = tam / TIPO.upm
        ancho = total * esc
        x0 = x - (ancho if ancla == "end" else ancho / 2 if ancla == "middle" else 0)
        usos, pluma = [], 0.0
        for gid, avance, dx, dy in gl:
            ref = self._glifo(gid, peso, opsz)
            if ref:
                usos.append(f'<use href="#{ref}" x="{n(pluma + dx, 1)}"' + (f' y="{n(dy, 1)}"' if dy else "") + "/>")
            pluma += avance + paso
        grupo = (f'<g transform="translate({n(x0)} {n(y)}) scale({n(esc, 5)} {n(-esc, 5)})" '
                 f'fill="{relleno}"{extra}>{"".join(usos)}</g>')
        return grupo, ancho

    def svg(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n(self.w)} {n(self.h)}" '
            f'width="{n(self.w)}" height="{n(self.h)}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{escape(self.titulo)}</title>\n<desc id="d">{escape(self.descripcion)}</desc>\n'
            f'<style>{"".join(self.css)}</style>\n'
            f'<defs>{"".join(self.defs)}</defs>\n'
            + "\n".join(self.cuerpo) + "\n</svg>\n"
        )


# ── Piezas comunes ──────────────────────────────────────────────────────────────────────────
def degradado_luz(doc: Documento, color: str, fuerza: float) -> str:
    gid = doc.uid("luz")
    doc.defs.append(
        f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{n(fuerza, 3)}"/>'
        f'<stop offset="0.72" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    return gid


def foco(doc: Documento, color: str, fuerza: float, cx: float, cy: float, rx: float, ry: float, clase: str) -> str:
    gid = degradado_luz(doc, color, fuerza)
    return f'<g class="{clase}"><ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="url(#{gid})"/></g>'


def sombra(doc: Documento, x, y, w, h, r, color, opacidad, desv, dy, encoge) -> str:
    """box-shadow: 0 dy (2·desv) -encoge color."""
    fid = doc.uid("sombra")
    m = desv * 3 + encoge
    doc.defs.append(
        f'<filter id="{fid}" filterUnits="userSpaceOnUse" x="{n(x - m)}" y="{n(y - m + dy)}" '
        f'width="{n(w + 2 * m)}" height="{n(h + 2 * m)}"><feGaussianBlur stdDeviation="{n(desv)}"/></filter>')
    rr = max(0.0, r - encoge)
    return (f'<rect x="{n(x + encoge)}" y="{n(y + encoge + dy)}" width="{n(max(1, w - 2 * encoge))}" '
            f'height="{n(max(1, h - 2 * encoge))}" rx="{n(rr)}" fill="{color}" fill-opacity="{n(opacidad, 3)}" '
            f'filter="url(#{fid})"/>')


def canto(doc: Documento, T: dict, x, y, w, h, r) -> str:
    """El canto iluminado del vidrio: línea de luz arriba, casi nada abajo, y el aro que lo separa."""
    gid = doc.uid("canto")
    doc.defs.append(
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="{n(T["canto"], 3)}"/>'
        f'<stop offset="0.28" stop-color="#FFFFFF" stop-opacity="{n(T["canto"] * 0.25, 3)}"/>'
        f'<stop offset="0.7" stop-color="#FFFFFF" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="{n(T["canto"] * 0.22, 3)}"/></linearGradient>')
    color_anillo, op_anillo = T["anillo"]
    return (
        f'<rect x="{n(x - 0.5)}" y="{n(y - 0.5)}" width="{n(w + 1)}" height="{n(h + 1)}" rx="{n(r + 0.5)}" '
        f'fill="none" stroke="{color_anillo}" stroke-opacity="{n(op_anillo, 3)}"/>'
        f'<rect x="{n(x + 0.75)}" y="{n(y + 0.75)}" width="{n(w - 1.5)}" height="{n(h - 1.5)}" rx="{n(r - 0.75)}" '
        f'fill="none" stroke="url(#{gid})" stroke-width="1.5"/>')


def relleno_vidrio(doc: Documento, T: dict, clave: str = "vidrio") -> str:
    gid = doc.uid("vidrio")
    c = T["vidrio_color"]
    doc.defs.append(
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{c}" stop-opacity="{n(T[clave + "_alto"], 3)}"/>'
        f'<stop offset="1" stop-color="{c}" stop-opacity="{n(T[clave + "_bajo"], 3)}"/></linearGradient>')
    return f"url(#{gid})"


ICONOS = {
    # Trazos de 24×24, con stroke: se dibujan con el color que se les pase.
    "maletin": '<rect x="2.5" y="7" width="19" height="13.5" rx="3"/><path d="M8.5 7V5.5a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2V7M2.5 12.5h19"/>',
    "escudo": '<path d="M12 2.8 19.5 5.6v6.1c0 4.6-3.2 8.1-7.5 9.6-4.3-1.5-7.5-5-7.5-9.6V5.6z"/><path d="m8.7 12 2.3 2.3 4.4-4.6"/>',
    "flecha": '<path d="M7 17 17 7M8.5 7H17v8.5"/>',
}


def icono(nombre: str, x: float, y: float, tam: float, color: str, grosor: float = 2.0) -> str:
    e = tam / 24
    return (f'<g transform="translate({n(x)} {n(y)}) scale({n(e, 4)})" fill="none" stroke="{color}" '
            f'stroke-width="{n(grosor / e, 3)}" stroke-linecap="round" stroke-linejoin="round">{ICONOS[nombre]}</g>')


def guardar(doc: Documento, nombre: str) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    ruta = ASSETS / nombre
    ruta.write_text(doc.svg(), encoding="utf-8")
    return ruta


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  BANNER
# ══════════════════════════════════════════════════════════════════════════════════════════════
def banner(tema: str) -> Path:
    T = TEMAS[tema]
    C = CONTENIDO
    W, H, R = 1200, 480, 36
    doc = Documento(W, H, C["nombre"],
                    f'{C["nombre"]}: {C["lema"][0]}{C["lema"][1]}{C["lema"][2]} '
                    + " · ".join(t for _, t in C["capsula"]))

    # ── Escena: fondo, rejilla de puntos y focos de luz (lo que el vidrio tiene detrás) ──
    doc.defs.append(
        f'<pattern id="puntos" width="26" height="26" patternUnits="userSpaceOnUse">'
        f'<circle cx="13" cy="13" r="1.3" fill="{T["sobre"]}" fill-opacity="{n(T["puntos"], 3)}"/></pattern>'
        f'<radialGradient id="desvanece-g" cx="0.5" cy="0.62" r="0.62">'
        f'<stop offset="0" stop-color="#FFF" stop-opacity="1"/><stop offset="0.55" stop-color="#FFF" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="#FFF" stop-opacity="0"/></radialGradient>'
        f'<mask id="desvanece" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="url(#desvanece-g)"/></mask>'
        f'<clipPath id="marco"><rect width="{W}" height="{H}" rx="{R}"/></clipPath>')
    fh = T["fuerza_hero"]
    escena = (
        f'<g id="escena"><rect width="{W}" height="{H}" fill="{T["fondo"]}"/>'
        + foco(doc, T["luz_a"], fh, W * 0.14, H * -0.06, W * 0.58, H * 0.95, "deriva-a")
        + foco(doc, T["luz_b"], fh * 0.65, W * 0.94, H * 0.04, W * 0.46, H * 0.85, "deriva-b")
        + foco(doc, T["luz_a"], fh * 0.55, W * 0.64, H * 1.0, W * 0.62, H * 0.62, "deriva-c")
        # Un foco que pasa por detrás de la cápsula: sin color moviéndose detrás, el vidrio no se nota.
        + foco(doc, T["luz_b"], fh * 0.85, W * 0.34, H * 0.80, W * 0.24, H * 0.30, "deriva-d")
        + f'<rect width="{W}" height="{H}" fill="url(#puntos)" mask="url(#desvanece)"/></g>')
    doc.css.append(
        ".deriva-d { transform-box: fill-box; transform-origin: center; }"
        "@media (prefers-reduced-motion: no-preference) { .deriva-d { animation: deriva-d 14s ease-in-out -3s infinite alternate; } }"
        "@keyframes deriva-d { from { transform: translate(-15%, 4%) scale(1); } to { transform: translate(90%, -6%) scale(1.15); } }")

    # ── Texto ──
    cx = W / 2
    saludo, _ = doc.texto(C["saludo"], cx, 112, 30, 500, -0.012, "middle", T["texto2"])
    nombre, _ = doc.texto(C["nombre"], cx, 228, 136, 650, -0.048, "middle", T["texto"])

    tam_lema, peso_lema, track_lema = 46, 560, -0.028
    a, clave, b = C["lema"]
    wa = medir(a, tam_lema, peso_lema, track_lema)
    wk = medir(clave, tam_lema, peso_lema, track_lema)
    wb = medir(b, tam_lema, peso_lema, track_lema)
    hueco = tam_lema * track_lema * 1  # el interletraje entre trozos
    total = wa + wk + wb + 2 * hueco
    x0 = cx - total / 2
    y_lema = 300
    trozo_a, _ = doc.texto(a, x0, y_lema, tam_lema, peso_lema, track_lema, "start", T["texto2"])
    xk = x0 + wa + hueco
    trozo_k, _ = doc.texto(clave, xk, y_lema, tam_lema, peso_lema, track_lema, "start", T["acento"])
    mascara_k, _ = doc.texto(clave, xk, y_lema, tam_lema, peso_lema, track_lema, "start", "#FFFFFF")
    trozo_b, _ = doc.texto(b, xk + wk + hueco, y_lema, tam_lema, peso_lema, track_lema, "start", T["texto2"])

    # El brillo turquesa del titular de Motorflux: cruza la palabra clave una vez, de ida y vuelta
    # desde el centro, y se queda en el centro (también con movimiento reducido).
    ac, it, lb = T["acento"], T["intenso"], T["luz_b"]
    m1, m2 = mezcla(ac, it, T["mezcla_brillo"]), mezcla(ac, lb, 0.75)
    doc.defs.append(
        f'<linearGradient id="brillo-g" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{ac}"/><stop offset="0.3" stop-color="{ac}"/>'
        f'<stop offset="0.4167" stop-color="{m1}"/><stop offset="0.5" stop-color="{m2}"/>'
        f'<stop offset="0.5833" stop-color="{m1}"/><stop offset="0.7" stop-color="{ac}"/>'
        f'<stop offset="1" stop-color="{ac}"/></linearGradient>'
        f'<mask id="clave-m" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">{mascara_k}</mask>')
    salto = wk * 0.5
    doc.css.append(
        f"@media (prefers-reduced-motion: no-preference) {{ .brillo {{ animation: tono 8s ease-in-out 2.5s both; }} }}"
        f"@keyframes tono {{ 0%, 100% {{ transform: translateX(0); }} 25% {{ transform: translateX({n(salto)}px); }} "
        f"75% {{ transform: translateX({n(-salto)}px); }} }}")
    brillo = (f'<g mask="url(#clave-m)"><rect class="brillo" x="{n(xk - wk)}" y="{n(y_lema - tam_lema)}" '
              f'width="{n(wk * 3)}" height="{n(tam_lema * 1.4)}" fill="url(#brillo-g)"/></g>')

    # ── La cápsula de vidrio ──
    tam_c, peso_c, track_c = 23, 560, -0.012
    ic, hueco_ic, sep, pad = 24, 12, 30, 34
    segmentos = [(nom, txt, medir(txt, tam_c, peso_c, track_c)) for nom, txt in C["capsula"]]
    cap_w = pad * 2 + sum(ic + hueco_ic + w for _, _, w in segmentos) + sep * 2 * (len(segmentos) - 1)
    cap_h = 74
    cap_x, cap_y = cx - cap_w / 2, 346
    cr = cap_h / 2
    ccx, ccy = cx, cap_y + cap_h / 2

    m = 70
    doc.defs.append(
        f'<clipPath id="capsula"><rect x="{n(cap_x)}" y="{n(cap_y)}" width="{n(cap_w)}" height="{cap_h}" rx="{n(cr)}"/></clipPath>'
        f'<filter id="esmerilado" filterUnits="userSpaceOnUse" x="{n(cap_x - m)}" y="{n(cap_y - m)}" '
        f'width="{n(cap_w + 2 * m)}" height="{n(cap_h + 2 * m)}" color-interpolation-filters="sRGB">'
        f'<feGaussianBlur stdDeviation="9"/><feColorMatrix type="saturate" values="1.7"/></filter>'
        f'<filter id="esmerilado-suave" filterUnits="userSpaceOnUse" x="{n(cap_x - m)}" y="{n(cap_y - m)}" '
        f'width="{n(cap_w + 2 * m)}" height="{n(cap_h + 2 * m)}" color-interpolation-filters="sRGB">'
        f'<feGaussianBlur stdDeviation="2.5"/><feColorMatrix type="saturate" values="1.9"/></filter>'
        f'<filter id="pluma" x="-10%" y="-40%" width="120%" height="180%"><feGaussianBlur stdDeviation="4"/></filter>'
        f'<mask id="aro" maskUnits="userSpaceOnUse" x="{n(cap_x - 4)}" y="{n(cap_y - 4)}" width="{n(cap_w + 8)}" height="{cap_h + 8}">'
        f'<rect x="{n(cap_x)}" y="{n(cap_y)}" width="{n(cap_w)}" height="{cap_h}" rx="{n(cr)}" fill="#FFF"/>'
        f'<rect x="{n(cap_x + 9)}" y="{n(cap_y + 9)}" width="{n(cap_w - 18)}" height="{cap_h - 18}" rx="{n(cr - 9)}" '
        f'fill="#000" filter="url(#pluma)"/></mask>'
        f'<radialGradient id="reflejo" cx="0.18" cy="0" r="0.9"><stop offset="0" stop-color="#FFF" stop-opacity="{n(T["brillo"] * 0.6, 3)}"/>'
        f'<stop offset="1" stop-color="#FFF" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="barrido-g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFF" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#FFF" stop-opacity="{n(T["brillo"], 3)}"/><stop offset="1" stop-color="#FFF" stop-opacity="0"/></linearGradient>')
    lente = f'translate({n(ccx)} {n(ccy)}) scale(1.05) translate({n(-ccx)} {n(-ccy)})'
    lente_aro = f'translate({n(ccx)} {n(ccy)}) scale(1.16 1.5) translate({n(-ccx)} {n(-ccy)})'
    recorrido = cap_w + 360
    doc.css.append(
        f"@media (prefers-reduced-motion: no-preference) {{ .barrido {{ animation: barrido 2.2s cubic-bezier(0.3, 0.6, 0.3, 1) 1.5s both; }} }}"
        f"@keyframes barrido {{ from {{ transform: translateX(0); }} to {{ transform: translateX({n(recorrido)}px); }} }}")
    color_f, op_f = T["flotante"]
    contenido_cap = []
    x = cap_x + pad
    for i, (nom, txt, w) in enumerate(segmentos):
        if i:
            contenido_cap.append(
                f'<rect x="{n(x + sep - 0.5)}" y="{n(ccy - 14)}" width="1" height="28" fill="{T["sobre"]}" fill-opacity="0.16"/>')
            x += sep * 2
        contenido_cap.append(icono(nom, x, ccy - ic / 2, ic, T["acento"], 2.0))
        g, _ = doc.texto(txt, x + ic + hueco_ic, ccy + tam_c * 0.36, tam_c, peso_c, track_c, "start", T["texto"])
        contenido_cap.append(g)
        x += ic + hueco_ic + w
    capsula = (
        sombra(doc, cap_x, cap_y, cap_w, cap_h, cr, T["sombra"][0], T["sombra"][1] * 0.75, 20, 16, 16)
        + f'<g clip-path="url(#capsula)">'
        f'<use href="#escena" filter="url(#esmerilado)" transform="{lente}"/>'
        f'<g mask="url(#aro)"><use href="#escena" filter="url(#esmerilado-suave)" transform="{lente_aro}"/></g>'
        f'<rect x="{n(cap_x)}" y="{n(cap_y)}" width="{n(cap_w)}" height="{cap_h}" fill="{color_f}" fill-opacity="{n(op_f, 3)}"/>'
        f'<rect x="{n(cap_x)}" y="{n(cap_y)}" width="{n(cap_w)}" height="{cap_h}" fill="url(#reflejo)"/>'
        f'<g transform="translate({n(cap_x - 260)} {n(cap_y)}) skewX(-18)"><rect class="barrido" x="0" y="-10" width="150" '
        f'height="{cap_h + 20}" fill="url(#barrido-g)"/></g>'
        f'</g>'
        + canto(doc, T, cap_x, cap_y, cap_w, cap_h, cr)
        + "".join(contenido_cap))

    borde_c, borde_o = T["anillo"]
    doc.cuerpo += [
        f'<g clip-path="url(#marco)">',
        escena,
        f'<g class="entra" style="animation-delay:0.05s">{saludo}</g>',
        f'<g class="entra" style="animation-delay:0.12s">{nombre}</g>',
        f'<g class="entra" style="animation-delay:0.24s">{trozo_a}{trozo_k}{brillo}{trozo_b}</g>',
        f'<g class="entra" style="animation-delay:0.4s">{capsula}</g>',
        "</g>",
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="{R - 0.5}" fill="none" stroke="{borde_c}" '
        f'stroke-opacity="{n(borde_o * 1.2, 3)}"/>',
    ]
    return guardar(doc, f"banner-{tema}.svg")


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  TARJETAS DE PROYECTO
# ══════════════════════════════════════════════════════════════════════════════════════════════
def b64(ruta: Path, tipo: str) -> str:
    return f"data:{tipo};base64,{base64.b64encode(ruta.read_bytes()).decode()}"


def icono_proyecto(doc: Documento, T: dict, cual: str, x: float, y: float, s: float) -> str:
    r = s * 0.24
    pieza = sombra(doc, x, y, s, s, r, "#0B1A2E", 0.30 if T is TEMAS["claro"] else 0.55, 9, 10, 8)
    if cual == "motorflux":
        crudo = (AQUI / "marcas" / "motorflux-favicon.svg").read_text(encoding="utf-8")
        interior = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", crudo, flags=re.S)
        interior = re.sub(r'id="(t\d)"', r'id="mf-\1"', interior).replace("url(#t", "url(#mf-t")
        return pieza + f'<svg x="{n(x)}" y="{n(y)}" width="{n(s)}" height="{n(s)}" viewBox="0 0 512 512">{interior}</svg>'
    if cual == "bella":
        lado = s * 0.66
        return (pieza + f'<rect x="{n(x)}" y="{n(y)}" width="{n(s)}" height="{n(s)}" rx="{n(r)}" fill="#F3EDE4"/>'
                f'<rect x="{n(x + 0.5)}" y="{n(y + 0.5)}" width="{n(s - 1)}" height="{n(s - 1)}" rx="{n(r)}" fill="none" stroke="#8D6B50" stroke-opacity="0.18"/>'
                f'<image href="{b64(AQUI / "marcas" / "bella-isotipo.png", "image/png")}" x="{n(x + (s - lado) / 2)}" '
                f'y="{n(y + (s - lado) / 2)}" width="{n(lado)}" height="{n(lado)}"/>')
    if cual == "erizocoach":
        lado = s * 0.9
        return (pieza + f'<rect x="{n(x)}" y="{n(y)}" width="{n(s)}" height="{n(s)}" rx="{n(r)}" fill="#FFF8EC"/>'
                f'<rect x="{n(x + 0.5)}" y="{n(y + 0.5)}" width="{n(s - 1)}" height="{n(s - 1)}" rx="{n(r)}" fill="none" stroke="#7A4A1E" stroke-opacity="0.14"/>'
                f'<image href="{b64(AQUI / "marcas" / "erizocoach-176.png", "image/png")}" x="{n(x + (s - lado) / 2)}" '
                f'y="{n(y + (s - lado) / 2 + 1)}" width="{n(lado)}" height="{n(lado)}"/>')
    # escudo: el proyecto de puesta en producción segura
    gid = doc.uid("pieza")
    doc.defs.append(
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{T["luz_a"]}"/>'
        f'<stop offset="1" stop-color="{T["intenso"]}"/></linearGradient>')
    e = s / 72
    return (pieza + f'<rect x="{n(x)}" y="{n(y)}" width="{n(s)}" height="{n(s)}" rx="{n(r)}" fill="url(#{gid})"/>'
            f'<rect x="{n(x + 0.75)}" y="{n(y + 0.75)}" width="{n(s - 1.5)}" height="{n(s - 1.5)}" rx="{n(r)}" fill="none" stroke="#FFF" stroke-opacity="0.35" stroke-width="1.5"/>'
            f'<g transform="translate({n(x)} {n(y)}) scale({n(e, 4)})">'
            f'<path d="M36 15 53 21.5v13c0 10.4-7.1 18.2-17 21.5-9.9-3.3-17-11.1-17-21.5v-13z" fill="#FFF"/>'
            f'<path d="m28.5 35.5 5.2 5.2 9.8-10.4" fill="none" stroke="{T["intenso"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></g>')


def tarjeta(tema: str, p: dict, indice: int) -> Path:
    T = TEMAS[tema]
    W, H = 560, 380
    x, y, w, h, r = 18, 12, 524, 344, 30
    doc = Documento(W, H, p["nombre"], f'{p["nombre"]}: {p["texto"]} ({p["etiqueta"]})')
    clip = doc.uid("tarjeta")
    doc.defs.append(f'<clipPath id="{clip}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath>')

    cual, fx, fy = p["luz"]
    color = T["luz_a"] if cual == "a" else T["luz_b"]
    otro = T["luz_b"] if cual == "a" else T["luz_a"]
    campo = (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{T["fondo"]}"/>'
        + foco(doc, color, T["fuerza"] * T["luz_tarjeta"][0], x + w * fx, y + h * fy, w * 0.78, h * 1.05, "deriva-a")
        + foco(doc, otro, T["fuerza"] * T["luz_tarjeta"][1], x + w * (1 - fx), y + h * (1 - fy), w * 0.6, h * 0.8, "deriva-c")
        + f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{relleno_vidrio(doc, T, "tarjeta")}"/>')

    pad = 40
    s = 68
    pieza = icono_proyecto(doc, T, p["icono"], x + pad, y + pad, s)

    # Enlace: la única acción de la tarjeta, la única cosa teñida.
    tam_e, peso_e = 17, 600
    we = medir(p["etiqueta"], tam_e, peso_e, -0.01)
    eh, ew = 38, we + 18 + 16 + 14 + 18
    ex, ey = x + w - pad + 4 - ew, y + pad + s / 2 - eh / 2
    g_e, _ = doc.texto(p["etiqueta"], ex + 18, ey + eh / 2 + tam_e * 0.36, tam_e, peso_e, -0.01, "start", T["enlace"])
    enlace = (f'<rect x="{n(ex)}" y="{n(ey)}" width="{n(ew)}" height="{eh}" rx="{eh / 2}" fill="{T["intenso"]}" '
              f'fill-opacity="{n(T["tinte_enlace"], 3)}"/>' + g_e
              + icono("flecha", ex + 18 + we + 8, ey + eh / 2 - 8, 16, T["enlace"], 2.2))

    titulo, _ = doc.texto(p["nombre"], x + pad, y + 170, 40, 650, -0.032, "start", T["texto"])
    lineas = partir(p["texto"], 21, 460, w - pad * 2, -0.008)
    if len(lineas) > 2:
        raise SystemExit(f'El texto de «{p["nombre"]}» ocupa {len(lineas)} líneas: acórtalo a dos.')
    parrafo = "".join(doc.texto(l, x + pad, y + 210 + i * 30, 21, 460, -0.008, "start", T["texto2"])[0]
                      for i, l in enumerate(lineas))

    chips, cx_ = [], x + pad
    tam_ch, peso_ch, ch_h = 16, 560, 34
    cy_ = y + h - pad + 2 - ch_h
    for c in p["chips"]:
        wc = medir(c, tam_ch, peso_ch, -0.006) + 28
        g_c, _ = doc.texto(c, cx_ + 14, cy_ + ch_h / 2 + tam_ch * 0.36, tam_ch, peso_ch, -0.006, "start", T["chip_texto"])
        chips.append(f'<rect x="{n(cx_)}" y="{n(cy_)}" width="{n(wc)}" height="{ch_h}" rx="{ch_h / 2}" '
                     f'fill="{T["sobre"]}" fill-opacity="{n(T["relleno"], 3)}"/>' + g_c)
        cx_ += wc + 8

    borde_c, borde_o = T["borde"]
    doc.cuerpo += [
        f'<g class="entra" style="animation-delay:{n(0.08 + indice * 0.09)}s">',
        sombra(doc, x, y, w, h, r, T["sombra"][0], T["sombra"][1] * 0.9, 18, 18, 22),
        f'<g clip-path="url(#{clip})">{campo}</g>',
        f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{w - 1}" height="{h - 1}" rx="{r - 0.5}" fill="none" '
        f'stroke="{borde_c}" stroke-opacity="{n(borde_o, 3)}"/>',
        canto(doc, T, x, y, w, h, r),
        pieza, enlace, titulo, parrafo, "".join(chips),
        "</g>",
    ]
    return guardar(doc, f'proyecto-{p["id"]}-{tema}.svg')


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  TECNOLOGÍAS
# ══════════════════════════════════════════════════════════════════════════════════════════════
def tecnologias(tema: str) -> Path:
    T = TEMAS[tema]
    filas = CONTENIDO["tecnologias"]
    W, R = 1200, 32
    pad_x, pad_y, alto_fila, ch_h = 52, 46, 70, 46
    H = pad_y * 2 + alto_fila * len(filas) - (alto_fila - ch_h)
    doc = Documento(W, H, "Con qué trabajo",
                    " · ".join(f'{nombre}: {", ".join(items)}' for nombre, items in filas))
    doc.defs.append(f'<clipPath id="marco"><rect width="{W}" height="{H}" rx="{R}"/></clipPath>')
    campo = (
        f'<rect width="{W}" height="{H}" fill="{T["fondo"]}"/>'
        + foco(doc, T["luz_a"], T["fuerza_hero"], W * 0.08, H * 0.1, W * 0.5, H * 1.3, "deriva-a")
        + foco(doc, T["luz_b"], T["fuerza_hero"] * 0.7, W * 0.92, H * 0.95, W * 0.46, H * 1.2, "deriva-b"))
    vidrio = relleno_vidrio(doc, T)
    borde_c, borde_o = T["borde"]
    piezas, k = [], 0
    col = 236
    for i, (nombre, items) in enumerate(filas):
        yc = pad_y + i * alto_fila + ch_h / 2
        g_n, _ = doc.texto(nombre, pad_x, yc + 20 * 0.36, 20, 600, -0.012, "start", T["texto2"])
        piezas.append(f'<g class="entra" style="animation-delay:{n(0.05 + i * 0.08)}s">{g_n}</g>')
        x = pad_x + col
        for item in items:
            wt = medir(item, 20, 560, -0.01)
            wc = wt + 30 + 16
            g_t, _ = doc.texto(item, x + 30, yc + 20 * 0.36, 20, 560, -0.01, "start", T["texto"])
            y0 = yc - ch_h / 2
            piezas.append(
                f'<g class="entra" style="animation-delay:{n(0.1 + i * 0.08 + k * 0.025)}s">'
                + sombra(doc, x, y0, wc, ch_h, ch_h / 2, T["sombra"][0], T["sombra"][1] * 0.6, 8, 8, 6)
                + f'<rect x="{n(x)}" y="{n(y0)}" width="{n(wc)}" height="{ch_h}" rx="{ch_h / 2}" fill="{T["fondo"]}"/>'
                f'<rect x="{n(x)}" y="{n(y0)}" width="{n(wc)}" height="{ch_h}" rx="{ch_h / 2}" fill="{vidrio}"/>'
                f'<rect x="{n(x + 0.5)}" y="{n(y0 + 0.5)}" width="{n(wc - 1)}" height="{ch_h - 1}" rx="{ch_h / 2 - 0.5}" fill="none" stroke="{borde_c}" stroke-opacity="{n(borde_o, 3)}"/>'
                + canto(doc, T, x, y0, wc, ch_h, ch_h / 2)
                + f'<circle cx="{n(x + 18)}" cy="{n(yc)}" r="4" fill="{T["acento"]}"/>' + g_t + "</g>")
            x += wc + 10
            k += 1
        if x - 10 > W - pad_x:
            raise SystemExit(f"La fila «{nombre}» no cabe: quita alguna tecnología.")
    doc.cuerpo += [
        f'<g clip-path="url(#marco)">{campo}</g>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="{R - 0.5}" fill="none" stroke="{T["anillo"][0]}" '
        f'stroke-opacity="{n(T["anillo"][1] * 1.2, 3)}"/>',
        *piezas,
    ]
    return guardar(doc, f"tecnologias-{tema}.svg")


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  BOTONES DE CONTACTO
# ══════════════════════════════════════════════════════════════════════════════════════════════
def boton(tema: str, red: str) -> Path:
    T = TEMAS[tema]
    etiqueta = {"linkedin": "LinkedIn", "instagram": "Instagram"}[red]
    tam, peso = 25, 600
    wt = medir(etiqueta, tam, peso, -0.012)
    bh, ic = 62, 28
    bw = 26 + ic + 12 + wt + 30
    W, H = bw + 36, bh + 40
    x, y = 18, 12
    doc = Documento(W, H, etiqueta, f"{etiqueta} de {CONTENIDO['nombre']}")
    r = bh / 2
    yc = y + bh / 2
    if red == "linkedin":
        # El botón principal: azul lleno y texto blanco (5,9:1), como «Solicitar demo» en Motorflux.
        g_t, _ = doc.texto(etiqueta, x + 26 + ic + 12, yc + tam * 0.36, tam, peso, -0.012, "start", "#FFFFFF")
        g_in, _ = doc.texto("in", x + 26 + ic / 2 + 0.5, yc + 7, 19, 750, -0.02, "middle", T["intenso"])
        fondo = (sombra(doc, x, y, bw, bh, r, T["intenso"], 0.42, 12, 12, 10)
                 + f'<rect x="{x}" y="{y}" width="{n(bw)}" height="{bh}" rx="{r}" fill="{T["intenso"]}"/>'
                 f'<rect x="{x + 0.75}" y="{y + 0.75}" width="{n(bw - 1.5)}" height="{bh - 1.5}" rx="{r - 0.75}" fill="none" '
                 f'stroke="url(#luz-boton)" stroke-width="1.5"/>')
        doc.defs.append(
            '<linearGradient id="luz-boton" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF" stop-opacity="0.4"/>'
            '<stop offset="0.35" stop-color="#FFF" stop-opacity="0"/></linearGradient>')
        marca = (f'<rect x="{x + 26}" y="{n(yc - ic / 2)}" width="{ic}" height="{ic}" rx="7" fill="#FFFFFF"/>' + g_in)
    else:
        g_t, _ = doc.texto(etiqueta, x + 26 + ic + 12, yc + tam * 0.36, tam, peso, -0.012, "start", T["texto"])
        borde_c, borde_o = T["borde"]
        fondo = (sombra(doc, x, y, bw, bh, r, T["sombra"][0], T["sombra"][1] * 0.7, 12, 12, 10)
                 + f'<rect x="{x}" y="{y}" width="{n(bw)}" height="{bh}" rx="{r}" fill="{T["fondo"]}"/>'
                 f'<rect x="{x}" y="{y}" width="{n(bw)}" height="{bh}" rx="{r}" fill="{relleno_vidrio(doc, T)}"/>'
                 f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{n(bw - 1)}" height="{bh - 1}" rx="{r - 0.5}" fill="none" '
                 f'stroke="{borde_c}" stroke-opacity="{n(borde_o, 3)}"/>' + canto(doc, T, x, y, bw, bh, r))
        e = ic / 24
        marca = (f'<g transform="translate({x + 26} {n(yc - ic / 2)}) scale({n(e, 4)})" fill="none" stroke="{T["texto"]}" '
                 f'stroke-width="{n(2.1 / e, 3)}"><rect x="2.5" y="2.5" width="19" height="19" rx="5.5"/>'
                 f'<circle cx="12" cy="12" r="4.4"/><circle cx="17.4" cy="6.6" r="0.6" fill="{T["texto"]}"/></g>')
    doc.cuerpo.append(f'<g class="entra" style="animation-delay:{0.1 if red == "linkedin" else 0.18}s">'
                      f'{fondo}{marca}{g_t}</g>')
    return guardar(doc, f"boton-{red}-{tema}.svg")


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  README
# ══════════════════════════════════════════════════════════════════════════════════════════════
def imagen(base: str, alt: str, atributos: str) -> str:
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{base}-oscuro.svg">'
            f'<img src="assets/{base}-claro.svg" alt="{escape(alt, {chr(34): "&quot;"})}" {atributos}></picture>')


def readme() -> Path:
    C = CONTENIDO
    p = C["proyectos"]

    def tarjeta_html(pr: dict) -> str:
        return (f'<a href="{pr["enlace"]}">'
                + imagen(f'proyecto-{pr["id"]}', f'{pr["nombre"]}: {pr["texto"]}', 'width="49%"') + "</a>")

    # Todas en un solo párrafo centrado: al 49 % caben dos por línea, el hueco entre filas queda igual
    # que el de entre columnas (con un párrafo por fila, el margen del párrafo lo doblaba) y, si son
    # impares, la última queda centrada.
    filas = '<p align="center">\n  ' + "\n  ".join(tarjeta_html(pr) for pr in p) + "\n</p>"
    raw = f"https://raw.githubusercontent.com/{USUARIO}/{USUARIO}/output"
    lema = "".join(C["lema"])
    texto = f"""<!-- Generado por generador/generar.py: cambia los textos allí y vuelve a ejecutarlo. -->
<p align="center">
  {imagen("banner", f'{C["nombre"]}: {lema} ' + " · ".join(t for _, t in C["capsula"]), 'width="100%"')}
</p>

<p align="center">
  <a href="{C["linkedin"]}">{imagen("boton-linkedin", "LinkedIn", 'height="52"')}</a>
  <a href="{C["instagram"]}">{imagen("boton-instagram", "Instagram", 'height="52"')}</a>
</p>

<h3 align="center">Sobre mí</h3>

<p align="center">
  {"<br>\n  ".join(C["sobre_mi"])}
</p>

<h3 align="center">Proyectos</h3>

{filas}

<h3 align="center">Con qué trabajo</h3>

<p align="center">
  {imagen("tecnologias", "Con qué trabajo: " + "; ".join(f'{a}: {", ".join(b)}' for a, b in C["tecnologias"]), 'width="100%"')}
</p>

<h3 align="center">Actividad</h3>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="{raw}/serpiente-oscuro.svg">
    <img src="{raw}/serpiente-claro.svg" alt="Mi gráfico de contribuciones, recorrido por una serpiente" width="100%">
  </picture>
</p>
"""
    ruta = REPO / "README.md"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def main() -> None:
    hechos = []
    for tema in TEMAS:
        hechos.append(banner(tema))
        for i, pr in enumerate(CONTENIDO["proyectos"]):
            hechos.append(tarjeta(tema, pr, i))
        hechos.append(tecnologias(tema))
        hechos.append(boton(tema, "linkedin"))
        hechos.append(boton(tema, "instagram"))
    hechos.append(readme())
    # Lo que ya no sale (un proyecto quitado de CONTENIDO, por ejemplo) se borra de assets/.
    for viejo in set(ASSETS.glob("*.svg")) - set(hechos):
        viejo.unlink()
        print(f"   borrado  {viejo.relative_to(REPO)}")
    for h in hechos:
        print(f"{h.stat().st_size / 1024:6.1f} KB  {h.relative_to(REPO)}")


if __name__ == "__main__":
    main()
