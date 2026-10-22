"""Parser del HTML de books.toscrape.com (listado y detalle) con html.parser.

html.parser (stdlib) en lugar de regex: es un parser real, tolerante al orden
y al espaciado del HTML, y mantiene el punto de "sin dependencias de runtime".
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin

from .models import Book

# quedan como regex SOLO en textos planos ya separados del markup
PAGER_TOTAL_RE = re.compile(r"Page \d+ of (\d+)")
STOCK_RE = re.compile(r"In stock \((\d+) available\)")

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def _class_of(attrs: list[tuple[str, str | None]]) -> str:
    for name, value in attrs:
        if name == "class":
            return value or ""
    return ""


def _href_of(attrs: list[tuple[str, str | None]]) -> str | None:
    for name, value in attrs:
        if name == "href" and value:
            return value
    return None


class _ListingParser(HTMLParser):
    """Extrae por página de listado: href del h3 de cada product_pod y href del next."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pod_hrefs: list[str] = []
        self.next_href: str | None = None
        self.text_all: list[str] = []
        self._in_pod = False
        self._in_pod_h3 = False
        self._in_next = False

    def handle_starttag(self, tag, attrs):
        klass = _class_of(attrs)
        if tag == "article" and "product_pod" in klass.split():
            self._in_pod = True
        elif self._in_pod and tag == "h3":
            self._in_pod_h3 = True
        elif self._in_pod_h3 and tag == "a":
            href = _href_of(attrs)
            if href:
                self.pod_hrefs.append(href)
        elif tag == "li" and "next" in klass.split():
            self._in_next = True
        elif self._in_next and tag == "a":
            href = _href_of(attrs)
            if href and self.next_href is None:
                self.next_href = href

    def handle_endtag(self, tag):
        if tag == "h3":
            self._in_pod_h3 = False
        elif tag == "article":
            self._in_pod = False
        elif tag == "li":
            self._in_next = False

    def handle_data(self, data):
        self.text_all.append(data)


class _DetailParser(HTMLParser):
    """Extrae de la página de detalle: título, precio, rating, stock y breadcrumb."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.price_raw = ""
        self.rating_word = ""
        self.stock_text = ""
        self.crumb_links: list[str] = []
        self._pmain_depth: int | None = None  # None = fuera del div.product_main
        self._in_h1 = False
        self._in_price = False
        self._in_stock = False
        self._in_breadcrumb = False
        self._in_crumb_a = False
        self._title: list[str] = []
        self._price: list[str] = []
        self._stock: list[str] = []
        self._crumb: list[str] = []

    def handle_starttag(self, tag, attrs):
        klass = _class_of(attrs)
        parts = klass.split()
        if tag == "div":
            if self._pmain_depth is None and "product_main" in parts:
                self._pmain_depth = 0
            elif self._pmain_depth is not None:
                self._pmain_depth += 1
        elif self._inside_main and tag == "h1":
            self._in_h1 = True
        elif self._inside_main and tag == "p" and "price_color" in parts and self.price_raw == "":
            self._in_price = True
        elif tag == "p" and "star-rating" in parts:
            for word in parts:
                if word != "star-rating" and self.rating_word == "":
                    self.rating_word = word
        elif tag == "p" and "instock" in parts:
            self._in_stock = True
        elif tag == "ul" and "breadcrumb" in parts:
            self._in_breadcrumb = True
        elif self._in_breadcrumb and tag == "a":
            self._in_crumb_a = True

    @property
    def _inside_main(self) -> bool:
        return self._pmain_depth is not None

    def handle_data(self, data):
        if self._in_h1:
            self._title.append(data)
        if self._in_price:
            self._price.append(data)
        if self._in_stock:
            self._stock.append(data)
        if self._in_crumb_a:
            self._crumb.append(data)

    def handle_endtag(self, tag):
        if tag == "div" and self._pmain_depth is not None:
            self._pmain_depth = None if self._pmain_depth == 0 else self._pmain_depth - 1
        elif tag == "h1" and self._in_h1:
            self.title = "".join(self._title).strip()
            self._in_h1 = False
        elif tag == "p" and self._in_price:
            self.price_raw = "".join(self._price).strip()
            self._in_price = False
        elif tag == "p" and self._in_stock:
            self.stock_text = "".join(self._stock).strip()
            self._in_stock = False
        elif tag == "a" and self._in_crumb_a:
            text = "".join(self._crumb).strip()
            if text:
                self.crumb_links.append(text)
            self._crumb = []
            self._in_crumb_a = False
        elif tag == "ul" and self._in_breadcrumb:
            self._in_breadcrumb = False


def parse_listing(page: str) -> tuple[list[str], str | None, int]:
    """(hrefs relativos de libros, href del next [None al final], páginas totales)."""
    parser = _ListingParser()
    parser.feed(page)
    parser.close()
    next_href = parser.next_href
    if next_href == "#":  # enlace "next" deshabilitado en la última página
        next_href = None
    m_total = PAGER_TOTAL_RE.search("".join(parser.text_all))
    total_pages = int(m_total.group(1)) if m_total else 0
    return parser.pod_hrefs, next_href, total_pages


def _split_price(text: str) -> tuple[float, str]:
    """'£51.77' -> (51.77, '£'). Lanza ValueError si el precio es ilegible."""
    digits = re.search(r"([\d.,]+)", text)
    if not digits:
        raise ValueError(f"precio ilegible: {text!r}")
    currency_m = re.match(r"^([^\d.,]+)", text)
    currency = currency_m.group(1).strip() if currency_m else ""
    return float(digits.group(1).replace(",", "")), currency


def parse_detail(page: str, url: str) -> Book:
    """Extrae la fila completa de la página de detalle; ValueError si falta algo esencial."""
    parser = _DetailParser()
    parser.feed(page)
    parser.close()

    missing: list[str] = []
    if not parser.title:
        missing.append("title")
    if not parser.price_raw:
        missing.append("price")
    if not parser.rating_word:
        missing.append("rating")
    stock_m = STOCK_RE.search(parser.stock_text)
    if not stock_m:
        missing.append("stock")
    if len(parser.crumb_links) < 3:
        missing.append(
            "breadcrumb incompleto (%s)" % ", ".join(parser.crumb_links)
            if parser.crumb_links
            else "breadcrumb ausente"
        )

    if missing:
        raise ValueError(f"campos ausentes en detalle ({url}): {', '.join(missing)}")

    assert stock_m is not None  # cubierto por missing
    price_number, price_currency = _split_price(parser.price_raw)
    rating = RATING_WORDS.get(parser.rating_word, 0)
    return Book(
        title=parser.title,
        price_number=price_number,
        price_currency=price_currency,
        rating=rating,
        stock=int(stock_m.group(1)),
        category=parser.crumb_links[-1],
        url=url,
    )


def absolute_book_url(page_url: str, href: str) -> str:
    """URL absoluto del detalle resolviendo el href relativo del listado."""
    return urljoin(page_url, href)
