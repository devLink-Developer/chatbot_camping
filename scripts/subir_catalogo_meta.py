"""
Sube o actualiza items en un catalogo de Meta (Facebook) usando fotos locales.

Fuentes:
- fotos_camping/catalogo.json (metadatos, si existe)
- fotos_camping/** (imagenes locales; incluye fotos nuevas no listadas)

Ejemplo (prueba):
    python scripts/subir_catalogo_meta.py --catalog-id 25089046237463444 --dry-run

Ejemplo (publicar):
    python scripts/subir_catalogo_meta.py --catalog-id 25089046237463444 --apply \
      --access-token "<TOKEN>" --image-base-url "https://tu-dominio.com/fotos_camping/"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests
from dotenv import load_dotenv


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_GRAPH_BASE = "https://graph.facebook.com"
DEFAULT_GRAPH_VERSION = "v25.0"
DEFAULT_PRODUCT_URL = "https://www.campinglujanaca.com"
DEFAULT_CURRENCY = "ARS"
DEFAULT_PRICE = "1.00"
DEFAULT_EXCLUDED_CATEGORIES = {"tarifas"}

# Puedes sobreescribir este mapping con --category-map-json.
DEFAULT_CATEGORY_MAP = {
    "bosque": "Bosque y Senderos Naturales",
    "camping": "Zona de Acampe",
    "deportes": "Deportes y Actividades",
    "general": "Instalaciones Generales",
    "instalaciones": "Instalaciones y Servicios",
    "logo": "Identidad de Marca",
    "naturaleza": "Fauna y Naturaleza",
    "pileta": "Piscina Recreativa",
    "recreacion": "Recreacion Familiar",
    "servicios": "Servicios del Camping",
    "tarifas": "Tarifas y Reservas",
}


@dataclass
class CatalogEntry:
    categoria_raw: str
    categoria_display: str
    descripcion: str
    archivo_rel: str | None
    image_url_fallback: str | None
    pagina: str | None


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "item"


def _norm_category_key(value: str) -> str:
    return _slug(value).replace("-", "_")


def _title_from_key(value: str) -> str:
    plain = re.sub(r"[_\-]+", " ", value).strip()
    if not plain:
        return "General"
    return " ".join(w.capitalize() for w in plain.split())


def _fix_mojibake(text: str) -> str:
    # Intenta reparar cadenas tipo "mÃ¡gico", "fÃºtbol", etc.
    s = (text or "").strip()
    if not s:
        return s
    for _ in range(2):
        if any(ch in s for ch in ("Ã", "Â", "â", "€", "™", "�")):
            try:
                candidate = s.encode("latin1").decode("utf-8")
                if candidate:
                    s = candidate
                    continue
            except Exception:
                pass
        break
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _norm_rel(path: Path, base_dir: Path) -> str:
    return path.relative_to(base_dir).as_posix()


def _iter_local_images(root_dir: Path) -> Iterable[Path]:
    for p in sorted(root_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def _load_category_map(path: Path | None) -> dict[str, str]:
    data = dict(DEFAULT_CATEGORY_MAP)
    if path and path.exists():
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for k, v in raw.items():
                key = _norm_category_key(str(k))
                val = _fix_mojibake(str(v)).strip()
                if key and val:
                    data[key] = val
    return data


def _parse_excluded_categories(raw: str | None) -> set[str]:
    if not raw:
        return set(DEFAULT_EXCLUDED_CATEGORIES)
    values = [v.strip() for v in raw.split(",") if v.strip()]
    if not values:
        return set(DEFAULT_EXCLUDED_CATEGORIES)
    return {_norm_category_key(v) for v in values}


def _resolve_category(raw_category: str, category_map: dict[str, str]) -> tuple[str, str]:
    raw = _fix_mojibake(raw_category or "general")
    key = _norm_category_key(raw)
    display = category_map.get(key) or _title_from_key(key)
    return key, display


def _load_json_entries(catalog_json: Path, category_map: dict[str, str]) -> dict[str, CatalogEntry]:
    if not catalog_json.exists():
        return {}

    with catalog_json.open("r", encoding="utf-8") as f:
        data = json.load(f)

    out: dict[str, CatalogEntry] = {}
    categorias = data.get("categorias") or {}
    for categoria, items in categorias.items():
        if not isinstance(items, list):
            continue
        for item in items:
            archivo_rel = item.get("archivo_local")
            if archivo_rel:
                archivo_rel = str(archivo_rel).replace("\\", "/")

            categoria_raw = str(item.get("categoria") or categoria or "general")
            key, display = _resolve_category(categoria_raw, category_map)
            entry = CatalogEntry(
                categoria_raw=key,
                categoria_display=display,
                descripcion=_fix_mojibake(str(item.get("descripcion") or "").strip() or "Foto del camping"),
                archivo_rel=archivo_rel,
                image_url_fallback=(str(item.get("url")) if item.get("url") else None),
                pagina=(str(item.get("pagina")) if item.get("pagina") else None),
            )

            if archivo_rel:
                out[archivo_rel] = entry

    return out


def _build_image_url(entry: CatalogEntry, image_base_url: str | None) -> str | None:
    if image_base_url and entry.archivo_rel:
        base = image_base_url.rstrip("/") + "/"
        parts = [quote(part) for part in entry.archivo_rel.split("/")]
        return base + "/".join(parts)
    return entry.image_url_fallback


def _build_product_url(entry: CatalogEntry, default_product_url: str) -> str:
    if entry.pagina:
        return f"{default_product_url.rstrip('/')}/{quote(entry.pagina)}"
    return default_product_url


def _make_entries(
    base_dir: Path,
    fotos_dir: Path,
    json_map: dict[str, CatalogEntry],
    include_local_only: bool,
    category_map: dict[str, str],
) -> list[CatalogEntry]:
    entries: list[CatalogEntry] = []
    used_rel: set[str] = set()

    # 1) Todas las imagenes locales (incluye fotos nuevas no listadas en JSON).
    for img in _iter_local_images(fotos_dir):
        rel = _norm_rel(img, base_dir)
        used_rel.add(rel)
        if rel in json_map:
            e = json_map[rel]
            entries.append(
                CatalogEntry(
                    categoria_raw=e.categoria_raw,
                    categoria_display=e.categoria_display,
                    descripcion=e.descripcion,
                    archivo_rel=rel,
                    image_url_fallback=e.image_url_fallback,
                    pagina=e.pagina,
                )
            )
            continue

        key, display = _resolve_category(img.parent.name, category_map)
        desc = _fix_mojibake(img.stem.replace("_", " ").replace("-", " ").strip() or "Foto del camping")
        entries.append(
            CatalogEntry(
                categoria_raw=key,
                categoria_display=display,
                descripcion=desc,
                archivo_rel=rel,
                image_url_fallback=None,
                pagina=None,
            )
        )

    # 2) Opcional: tambien incluir entradas del JSON que no tienen archivo local.
    if not include_local_only:
        for rel, e in json_map.items():
            if rel in used_rel:
                continue
            entries.append(e)

    return entries


def _stable_retailer_id(prefix: str, entry: CatalogEntry) -> str:
    seed = entry.archivo_rel or entry.image_url_fallback or f"{entry.categoria_raw}:{entry.descripcion}"
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"{_slug(prefix)}-{h}"


def _build_payloads(
    entries: list[CatalogEntry],
    image_base_url: str | None,
    default_product_url: str,
    brand: str,
    currency: str,
    price: str,
    visibility: str,
    availability: str,
    condition: str,
    retailer_prefix: str,
) -> tuple[list[dict], list[dict]]:
    payloads: list[dict] = []
    skipped: list[dict] = []

    for e in entries:
        image_url = _build_image_url(e, image_base_url)
        if not image_url:
            skipped.append(
                {
                    "reason": "sin_image_url",
                    "categoria": e.categoria_display,
                    "descripcion": e.descripcion,
                    "archivo_rel": e.archivo_rel,
                }
            )
            continue

        payloads.append(
            {
                "retailer_id": _stable_retailer_id(retailer_prefix, e),
                "name": (e.descripcion[:150] or "Camping ACA Lujan"),
                "description": e.descripcion[:5000],
                "category": e.categoria_display,
                "product_type": e.categoria_display,
                "custom_label_0": e.categoria_raw,
                "brand": brand,
                "availability": availability,
                "condition": condition,
                "price": price,
                "currency": currency,
                "url": _build_product_url(e, default_product_url),
                "image_url": image_url,
                "visibility": visibility,
                "allow_upsert": "true",
            }
        )

    return payloads, skipped


def _post_product(
    graph_base: str,
    graph_version: str,
    catalog_id: str,
    access_token: str,
    data: dict,
    timeout: int,
) -> requests.Response:
    endpoint = f"{graph_base.rstrip('/')}/{graph_version}/{catalog_id}/products"
    body = dict(data)
    body["access_token"] = access_token
    return requests.post(endpoint, data=body, timeout=timeout)


def _validate_catalog_business(
    graph_base: str,
    graph_version: str,
    catalog_id: str,
    access_token: str,
    expected_business_id: str,
    timeout: int,
) -> tuple[bool, str]:
    endpoint = f"{graph_base.rstrip('/')}/{graph_version}/{catalog_id}"
    params = {
        "fields": "id,name,business{id,name}",
        "access_token": access_token,
    }
    try:
        resp = requests.get(endpoint, params=params, timeout=timeout)
        data = resp.json() if resp.content else {}
    except Exception as exc:
        return False, f"Error consultando Graph API para validar negocio: {exc}"

    if not resp.ok or "error" in data:
        err = data.get("error", data)
        return False, f"Error de API al validar catalogo/negocio: {err}"

    business = data.get("business") or {}
    found_business_id = str(business.get("id") or "").strip()
    expected = str(expected_business_id or "").strip()

    if not found_business_id:
        return False, "No se pudo obtener business.id del catalogo con este token."
    if found_business_id != expected:
        return (
            False,
            f"Token/catalogo pertenece a business_id={found_business_id}, no a business_id={expected}.",
        )

    name = business.get("name") or "(sin nombre)"
    return True, f"OK (business_id={found_business_id}, business_name={name})"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sube/actualiza productos en Meta Catalog usando fotos locales."
    )
    parser.add_argument("--catalog-id", required=True, help="ID del catalogo de Meta.")
    parser.add_argument(
        "--business-id",
        default=os.getenv("META_BUSINESS_ID", ""),
        help="Business ID esperado para validar token y catalogo (ej: 697192049324931).",
    )
    parser.add_argument(
        "--access-token",
        default=os.getenv("META_ACCESS_TOKEN") or os.getenv("WHATSAPP_ACCESS_TOKEN"),
        help="Token con permiso catalog_management.",
    )
    parser.add_argument("--graph-base", default=os.getenv("META_GRAPH_BASE", DEFAULT_GRAPH_BASE))
    parser.add_argument("--graph-version", default=os.getenv("META_GRAPH_VERSION", DEFAULT_GRAPH_VERSION))
    parser.add_argument("--fotos-dir", default="fotos_camping")
    parser.add_argument("--catalog-json", default="fotos_camping/catalogo.json")
    parser.add_argument(
        "--category-map-json",
        default="scripts/category_map.json",
        help="JSON opcional para mapear categorias (clave: carpeta, valor: categoria mostrada).",
    )
    parser.add_argument(
        "--image-base-url",
        default=os.getenv("META_IMAGE_BASE_URL"),
        help="Base publica para imagenes locales (ej: https://dominio/fotos_camping/).",
    )
    parser.add_argument(
        "--product-url",
        default=os.getenv("META_PRODUCT_URL", DEFAULT_PRODUCT_URL),
        help="URL base del producto/sitio.",
    )
    parser.add_argument("--brand", default=os.getenv("META_BRAND", "Camping ACA Lujan"))
    parser.add_argument("--currency", default=os.getenv("META_CURRENCY", DEFAULT_CURRENCY))
    parser.add_argument("--price", default=os.getenv("META_PRICE", DEFAULT_PRICE), help="Precio unitario string, ej: 1.00")
    parser.add_argument("--visibility", default=os.getenv("META_VISIBILITY", "published"), choices=["published", "staging"])
    parser.add_argument("--availability", default=os.getenv("META_AVAILABILITY", "in stock"))
    parser.add_argument("--condition", default=os.getenv("META_CONDITION", "new"))
    parser.add_argument("--retailer-prefix", default=os.getenv("META_RETAILER_PREFIX", "camping-lujan"))
    parser.add_argument(
        "--exclude-categories",
        default=os.getenv("META_EXCLUDE_CATEGORIES", "tarifas"),
        help="Categorias a excluir (separadas por coma), por ejemplo: tarifas,logo",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limita cantidad de items (0 = sin limite).")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--include-json-only", action="store_true", help="Incluye entradas del JSON aunque no exista archivo local.")
    parser.add_argument("--apply", action="store_true", help="Ejecuta llamadas reales a la API.")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra/resguarda payload sin enviar.")
    parser.add_argument("--output", default="fotos_camping/meta_payload_preview.json")
    return parser.parse_args()


def main() -> int:
    load_dotenv()

    args = parse_args()
    do_apply = bool(args.apply and not args.dry_run)

    base_dir = Path(__file__).resolve().parent.parent
    fotos_dir = (base_dir / args.fotos_dir).resolve()
    catalog_json = (base_dir / args.catalog_json).resolve()
    category_map_json = (base_dir / args.category_map_json).resolve()

    if not fotos_dir.exists():
        print(f"ERROR: no existe directorio de fotos: {fotos_dir}")
        return 2

    category_map = _load_category_map(category_map_json)
    excluded_categories = _parse_excluded_categories(args.exclude_categories)
    json_map = _load_json_entries(catalog_json, category_map)
    entries = _make_entries(
        base_dir=base_dir,
        fotos_dir=fotos_dir,
        json_map=json_map,
        include_local_only=not args.include_json_only,
        category_map=category_map,
    )
    entries_before_exclusion = len(entries)
    entries = [e for e in entries if e.categoria_raw not in excluded_categories]
    excluded_count = entries_before_exclusion - len(entries)

    payloads, skipped = _build_payloads(
        entries=entries,
        image_base_url=args.image_base_url,
        default_product_url=args.product_url,
        brand=args.brand,
        currency=args.currency,
        price=args.price,
        visibility=args.visibility,
        availability=args.availability,
        condition=args.condition,
        retailer_prefix=args.retailer_prefix,
    )

    if args.limit and args.limit > 0:
        payloads = payloads[: args.limit]

    category_counts = Counter(p["category"] for p in payloads)
    output_path = (base_dir / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "catalog_id": args.catalog_id,
                "graph_version": args.graph_version,
                "total_entries": len(entries),
                "total_payloads": len(payloads),
                "category_counts": dict(category_counts),
                "skipped": skipped,
                "payloads": payloads,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 72)
    print(f"Catalogo ID:         {args.catalog_id}")
    if args.business_id:
        print(f"Business ID esperado:{args.business_id}")
    print(f"Fotos dir:           {fotos_dir}")
    print(f"Catalog JSON:        {catalog_json} ({'OK' if catalog_json.exists() else 'NO ENCONTRADO'})")
    print(f"Category map JSON:   {category_map_json} ({'OK' if category_map_json.exists() else 'DEFAULT'})")
    print(f"Categorias excluidas:{', '.join(sorted(excluded_categories)) if excluded_categories else '(ninguna)'}")
    print(f"Total entradas:      {len(entries)}")
    print(f"Excluidas por regla: {excluded_count}")
    print(f"Listas para enviar:  {len(payloads)}")
    print(f"Saltadas:            {len(skipped)}")
    print(f"Preview payload:     {output_path}")
    print(f"Modo:                {'APPLY' if do_apply else 'DRY-RUN'}")
    print("=" * 72)

    if category_counts:
        print("Categorias detectadas:")
        for cat, qty in sorted(category_counts.items(), key=lambda x: x[0]):
            print(f"- {cat}: {qty}")

    if skipped:
        print("Primeras entradas saltadas:")
        for item in skipped[:5]:
            print(f"- {item.get('reason')}: {item.get('archivo_rel')} ({item.get('categoria')})")

    if not do_apply:
        print("\nNo se enviaron cambios. Usa --apply para publicar.")
        return 0

    if not args.access_token:
        print("ERROR: falta access token. Usa --access-token o META_ACCESS_TOKEN.")
        return 2

    if args.business_id:
        valid, message = _validate_catalog_business(
            graph_base=args.graph_base,
            graph_version=args.graph_version,
            catalog_id=args.catalog_id,
            access_token=args.access_token,
            expected_business_id=args.business_id,
            timeout=args.timeout,
        )
        print(f"Validacion business: {message}")
        if not valid:
            return 2

    ok = 0
    fail = 0
    for idx, payload in enumerate(payloads, start=1):
        try:
            resp = _post_product(
                graph_base=args.graph_base,
                graph_version=args.graph_version,
                catalog_id=args.catalog_id,
                access_token=args.access_token,
                data=payload,
                timeout=args.timeout,
            )
            data = resp.json() if resp.content else {}
            if resp.ok and "error" not in data:
                ok += 1
                print(f"[{idx:03d}/{len(payloads):03d}] OK   {payload['retailer_id']}")
            else:
                fail += 1
                err = data.get("error", data)
                print(f"[{idx:03d}/{len(payloads):03d}] FAIL {payload['retailer_id']} -> {err}")
        except Exception as exc:
            fail += 1
            print(f"[{idx:03d}/{len(payloads):03d}] FAIL {payload['retailer_id']} -> {exc}")

    print("\nResultado final:")
    print(f"- Exitos:   {ok}")
    print(f"- Fallas:   {fail}")
    print(f"- Total:    {len(payloads)}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
