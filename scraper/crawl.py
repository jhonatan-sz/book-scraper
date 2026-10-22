"""Crawl: recorre el listado (descubre URLs) y luego visita cada detalle."""

from __future__ import annotations

import logging
from typing import Protocol

from .fetch import DEFAULT_DELAY  # noqa: F401 (documentación por defecto)
from .models import Book
from .parse import absolute_book_url, parse_detail, parse_listing

MAX_LISTING_PAGES = 200
LISTING_URL_DEFAULT = "http://books.toscrape.com/catalogue/category/books_1/index.html"


class HttpFetcher(Protocol):
    def get(self, url: str) -> str: ...


def collect_book_urls(listing_url: str, fetcher: HttpFetcher, logger: logging.Logger) -> list[str]:
    """URLs absolutos de TODOS los libros, en orden de aparición, sin repetidos."""
    urls: list[str] = []
    seen: set[str] = set()
    page_url: str | None = listing_url
    pages = 0

    while page_url and pages < MAX_LISTING_PAGES:
        page = fetcher.get(page_url)
        hrefs, next_href, total = parse_listing(page)
        pages += 1
        nuevos = 0
        for href in hrefs:
            absolute = absolute_book_url(page_url, href)
            if absolute not in seen:
                seen.add(absolute)
                urls.append(absolute)
                nuevos += 1
        logger.info("listado p%d: +%d libros (next=%s, total=%s)", pages, nuevos, next_href, total)
        page_url = None if next_href is None else absolute_book_url(page_url, next_href)

    if pages >= MAX_LISTING_PAGES:
        logger.warning("tope de %d páginas del listado alcanzado; puede faltar catálogo", MAX_LISTING_PAGES)
    return urls


def scrape_books(
    listing_url: str,
    fetcher: HttpFetcher,
    logger: logging.Logger,
    *,
    max_books: int | None = None,
) -> tuple[list[Book], list[tuple[str, str]]]:
    """Descubre URLs del listado y devuelve (filas válidas, [(url, motivo)] inválidas)."""
    urls = collect_book_urls(listing_url, fetcher, logger)
    if max_books is not None:
        urls = urls[:max_books]

    books: list[Book] = []
    invalid: list[tuple[str, str]] = []

    for url in urls:
        page = fetcher.get(url)
        try:
            book = parse_detail(page, url)
        except ValueError as exc:
            logger.warning("fila invalida omitida: %s", exc)
            invalid.append((url, str(exc)))
            continue
        errs = validate_book(book)
        if errs:
            motivo = "; ".join(errs)
            logger.warning("fila invalida omitida (%s): %s", motivo, url)
            invalid.append((url, motivo))
            continue
        books.append(book)

    return books, invalid


def validate_book(book: Book) -> list[str]:
    """Envoltorio para no reimportar en cli.py."""
    from .models import validate  # import local evita el ciclo en pruebas con stubs

    return validate(book)
