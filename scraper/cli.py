"""CLI: python -m scraper --out books.csv (repetible, sin duplicados)."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time

from .crawl import LISTING_URL_DEFAULT, scrape_books
from .fetch import DEFAULT_DELAY, Fetcher
from .models import Book, CSV_COLUMNS


def write_csv(books: list[Book], path: str) -> None:
    """Escribe el CSV completo (encabezado + filas, en utf-8)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for book in books:
            writer.writerow([getattr(book, column) for column in CSV_COLUMNS])


def write_json(books: list[Book], path: str) -> None:
    """Escribe JSON (array de filas con las mismas columnas que el CSV, utf-8)."""
    rows = [{column: getattr(book, column) for column in CSV_COLUMNS} for book in books]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scraper",
        description="Scraper de books.toscrape.com -> CSV (practica; el sitio permite scraping)",
    )
    parser.add_argument("--out", default="books.csv", help="archivo CSV de salida")
    parser.add_argument("--listing-url", default=LISTING_URL_DEFAULT, help="semilla del crawl")
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"segundos de espera entre peticiones (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--max-books",
        type=int,
        default=None,
        help="tope de cheques de detalle (para pruebas rapidas)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="formato de salida (json para el paquete Premium)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger = logging.getLogger("scraper")

    fetcher = Fetcher(delay=args.delay)
    start = time.monotonic()
    books, invalid = scrape_books(
        args.listing_url, fetcher, logger=logger, max_books=args.max_books
    )
    write = write_json if args.format == "json" else write_csv
    write(books, args.out)
    elapsed = time.monotonic() - start

    logger.info(
        "RESULT filas=%d invalidas=%d segundos=%.1f salida=%s",
        len(books),
        len(invalid),
        elapsed,
        args.out,
    )
    if invalid:
        logger.info("primeras invalidas: %s", [url for url, _ in invalid[:5]])
    return 0
