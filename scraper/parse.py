"""Parser determinista del HTML de books.toscrape.com (listado y detalle)."""

from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from .models import Book

# listado: los article -> link del h3 con (title=)
LISTING_PRODUCT_RE = re.compile(r'<article class="product_pod">.*?<h3><a href="([^"]+)"', re.S)
NEXT_RE = re.compile(r'<li class="next"><a href="([^"]+)"')
PAGER_TOTAL_RE = re.compile(r"Page \d+ of (\d+)")

# detalle: la fuente canónica es la página del libro
TITLE_RE = re.compile(r'product_main">\s*<h1>([^<]+)</h1>')
PRICE_RE = re.compile(r'class="price_color">([^<]+?)\s*<')
RATING_RE = re.compile(r'class="star-rating (\w+)"')
STOCK_RE = re.compile(r"In stock \((\d+) available\)")
BREADCRUMB_RE = re.compile(r'<ul class="breadcrumb">(.*?)</ul>', re.S)
CRUMB_LINKS_RE = re.compile(r'<li[^>]*>\s*<a[^>]*>([^<]+)</a>')

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# ventana tras el h1 donde vive el precio canónico (evita "Incl. tax")
_PRICE_WINDOW = 1200


def parse_listing(page: str) -> tuple[list[str], str | None, int]:
    """(hrefs relativos de libros, href del next [None al final], páginas totales)."""
    hrefs = LISTING_PRODUCT_RE.findall(page)
    m_next = NEXT_RE.search(page)
    next_href = m_next.group(1) if m_next else None
    if next_href == "#":  # enlace "next" deshabilitado en la última página
        next_href = None
    m_total = PAGER_TOTAL_RE.search(page)
    total_pages = int(m_total.group(1)) if m_total else 0
    return hrefs, next_href, total_pages


def _split_price(text: str) -> tuple[float, str]:
    """'£51.77' -> (51.77, '£'). Lanza ValueError si el precio es ilegible."""
    digits = re.search(r"([\d.,]+)", text)
    if not digits:
        raise ValueError(f"precio ilegible: {text!r}")
    currency_m = re.match(r"^([^\d.,]+)", text)
    currency = currency_m.group(1).strip() if currency_m else ""
    return float(digits.group(1).replace(",", "")), currency


def _category_from_breadcrumb(page: str) -> str:
    """Breadcrumb Home > Books > <categoría> > título: la categoría es el último enlace."""
    m = BREADCRUMB_RE.search(page)
    if not m:
        raise ValueError("breadcrumb ausente")
    links = [html.unescape(t.strip()) for t in CRUMB_LINKS_RE.findall(m.group(1))]
    if len(links) < 3:  # Home, Books, <categoria>
        raise ValueError(f"breadcrumb incompleto ({links})")
    return links[-1]


def parse_detail(page: str, url: str) -> Book:
    """Extrae la fila completa de la página de detalle; ValueError si falta algo esencial."""
    missing: list[str] = []

    title_m = TITLE_RE.search(page)
    if not title_m:
        missing.append("title")
    price_m = PRICE_RE.search(page[title_m.end() : title_m.end() + _PRICE_WINDOW]) if title_m else None
    if not price_m:
        missing.append("price")
    rating_m = RATING_RE.search(page)
    if not rating_m:
        missing.append("rating")
    stock_m = STOCK_RE.search(page)
    if not stock_m:
        missing.append("stock")
    try:
        category = _category_from_breadcrumb(page)
    except ValueError as exc:
        category = ""
        missing.append(str(exc))

    if missing:
        raise ValueError(f"campos ausentes en detalle ({url}): {', '.join(missing)}")

    price_number, price_currency = _split_price(price_m.group(1).strip())
    rating = RATING_WORDS.get(rating_m.group(1), 0)
    return Book(
        title=html.unescape(title_m.group(1).strip()),
        price_number=price_number,
        price_currency=price_currency,
        rating=rating,
        stock=int(stock_m.group(1)),
        category=category,
        url=url,
    )


def absolute_book_url(page_url: str, href: str) -> str:
    """URL absoluto del detalle resolviendo el href relativo del listado."""
    return urljoin(page_url, href)
