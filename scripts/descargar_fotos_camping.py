"""
Descarga todas las fotos del sitio web del Camping ACA Luján
(https://www.campinglujanaca.com) y genera un catálogo JSON.

Uso:
    python scripts/descargar_fotos_camping.py
"""

import json
import os
import re
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

# ── Directorio destino ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FOTOS_DIR = BASE_DIR / "fotos_camping"
FOTOS_DIR.mkdir(exist_ok=True)

# ── Catálogo de fotos con URLs y categorías ─────────────────────────
# Recopiladas manualmente de todas las páginas del sitio.
FOTOS = [
    # ── HOME ──
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/new-05-v-copia_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista principal del camping - banner de inicio",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/ave-2.jpg?1644273107",
        "categoria": "naturaleza",
        "descripcion": "Ave en el bosque del camping",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/logo-aprobado.jpg?1644273504",
        "categoria": "logo",
        "descripcion": "Logo ACA aprobado",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/w-004_orig.jpg",
        "categoria": "instalaciones",
        "descripcion": "Vista general del predio",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/012_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 012",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/mg-7957_orig.jpg",
        "categoria": "general",
        "descripcion": "Fotografía profesional del camping",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/002_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 002",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/w-008_orig.jpg",
        "categoria": "instalaciones",
        "descripcion": "Instalaciones del camping",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/w-2-002_orig.jpg",
        "categoria": "instalaciones",
        "descripcion": "Instalaciones del camping (serie 2)",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/003_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 003",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/004_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 004",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/w-009_orig.jpg",
        "categoria": "instalaciones",
        "descripcion": "Instalaciones del camping",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/011_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 011",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/w-001_orig.jpg",
        "categoria": "instalaciones",
        "descripcion": "Instalaciones del camping",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/001_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 001",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/008_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 008",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/w-2-003_orig.jpg",
        "categoria": "instalaciones",
        "descripcion": "Instalaciones del camping (serie 2)",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/006_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 006",
        "pagina": "home",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/005_orig.jpg",
        "categoria": "general",
        "descripcion": "Vista del camping 005",
        "pagina": "home",
    },

    # ── SERVICIOS ──
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/l-01.jpg?1644501954",
        "categoria": "bosque",
        "descripcion": "El bosque - entorno mágico para descansar",
        "pagina": "servicios",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/a2_orig.jpg",
        "categoria": "camping",
        "descripcion": "Zona de acampe - parrillas, mesas, quinchos",
        "pagina": "servicios",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/m-01.jpg?1644501872",
        "categoria": "instalaciones",
        "descripcion": "Instalaciones de servicios del camping",
        "pagina": "servicios",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/prove_orig.jpg",
        "categoria": "servicios",
        "descripcion": "Proveeduría del camping",
        "pagina": "servicios",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/l-02.jpg?1644501949",
        "categoria": "bosque",
        "descripcion": "Vista del bosque del camping",
        "pagina": "servicios",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/a1_orig.jpg",
        "categoria": "recreacion",
        "descripcion": "Sector recreación - mesas, bancos, parrilleros",
        "pagina": "servicios",
    },

    # ── NOVEDADES ──
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/published/ave-1.jpg?1644523702",
        "categoria": "naturaleza",
        "descripcion": "Ave del camping - ellos te cantarán",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/camping-lujan-logo-instagram-final_orig.jpg",
        "categoria": "logo",
        "descripcion": "Logo Camping Luján para Instagram",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/pileta_orig.jpg",
        "categoria": "pileta",
        "descripcion": "Pileta de natación del camping",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/retocada_orig.jpg",
        "categoria": "deportes",
        "descripcion": "Deportes - fútbol, handball, pádel, tenis",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/bici-0_orig.jpg",
        "categoria": "deportes",
        "descripcion": "Alquiler de bicicletas",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/bici-2_orig.jpg",
        "categoria": "deportes",
        "descripcion": "Paseo en bicicleta por el bosque",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/tenis.jpg?1721342481",
        "categoria": "deportes",
        "descripcion": "Cancha de tenis",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/padel.jpg?1721342449",
        "categoria": "deportes",
        "descripcion": "Cancha de pádel",
        "pagina": "novedades",
    },

    # ── TARIFAS ──
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/reservas-25-copia_orig.jpg",
        "categoria": "tarifas",
        "descripcion": "Información de reservas y precios",
        "pagina": "tarifas",
    },

    # ── LOGOS (variantes) ──
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/editor/logo-final-png.png?1644501988",
        "categoria": "logo",
        "descripcion": "Logo final del Camping ACA Luján (servicios)",
        "pagina": "servicios",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/published/logo-final-png.png?1644523561",
        "categoria": "logo",
        "descripcion": "Logo final del Camping ACA Luján (novedades)",
        "pagina": "novedades",
    },
    {
        "url": "https://www.campinglujanaca.com/uploads/2/8/3/6/28362973/published/logo-final-png.png?1644526809",
        "categoria": "logo",
        "descripcion": "Logo final del Camping ACA Luján (tarifas)",
        "pagina": "tarifas",
    },
]


def _clean_filename(url: str) -> str:
    """Extrae un nombre de archivo limpio de la URL."""
    path = url.split("?")[0]  # quitar query string
    name = path.rsplit("/", 1)[-1]
    # reemplazar caracteres problemáticos
    name = re.sub(r"[^\w.\-]", "_", name)
    return name


def download_all():
    """Descarga todas las fotos y genera el catálogo."""
    # Crear sub-carpetas por categoría
    categorias = sorted({f["categoria"] for f in FOTOS})
    for cat in categorias:
        (FOTOS_DIR / cat).mkdir(exist_ok=True)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    catalogo = []
    descargadas = 0
    errores = 0
    vistas = set()  # evitar duplicados por URL base

    for foto in FOTOS:
        url_base = foto["url"].split("?")[0]
        if url_base in vistas:
            continue
        vistas.add(url_base)

        filename = _clean_filename(foto["url"])
        cat_dir = FOTOS_DIR / foto["categoria"]
        dest = cat_dir / filename

        print(f"  [{foto['categoria']:>14}] {filename} ... ", end="", flush=True)

        if dest.exists():
            print("YA EXISTE")
            catalogo.append({**foto, "archivo_local": str(dest.relative_to(BASE_DIR))})
            descargadas += 1
            continue

        try:
            req = urllib.request.Request(
                foto["url"],
                headers={"User-Agent": "Mozilla/5.0 (CampingBot/1.0)"},
            )
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read()
            dest.write_bytes(data)
            size_kb = len(data) / 1024
            print(f"OK ({size_kb:.0f} KB)")
            catalogo.append({
                **foto,
                "archivo_local": str(dest.relative_to(BASE_DIR)),
                "size_kb": round(size_kb, 1),
            })
            descargadas += 1
        except Exception as exc:
            print(f"ERROR: {exc}")
            catalogo.append({**foto, "archivo_local": None, "error": str(exc)})
            errores += 1

    # ── Guardar catálogo JSON ───────────────────────────────────────
    catalogo_path = FOTOS_DIR / "catalogo.json"
    with open(catalogo_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "fuente": "https://www.campinglujanaca.com",
                "fecha_descarga": datetime.now().isoformat(),
                "total_fotos": len(catalogo),
                "descargadas": descargadas,
                "errores": errores,
                "categorias": {
                    cat: [e for e in catalogo if e["categoria"] == cat]
                    for cat in categorias
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n{'='*60}")
    print(f"  Descargadas: {descargadas}")
    print(f"  Errores:     {errores}")
    print(f"  Catálogo:    {catalogo_path}")
    print(f"{'='*60}")

    # ── Resumen por categoría ───────────────────────────────────────
    print("\nResumen por categoría:")
    for cat in categorias:
        n = sum(1 for e in catalogo if e["categoria"] == cat and e.get("archivo_local"))
        print(f"  {cat:>14}: {n} fotos")


if __name__ == "__main__":
    print(f"Descargando fotos del Camping ACA Luján a {FOTOS_DIR}\n")
    download_all()
