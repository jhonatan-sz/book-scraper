"""Integración offline: crawl completo con fetcher falso (cero red)."""

import logging
import urllib.error
from pathlib import Path
from urllib.parse import urljoin

import pytest

from scraper.crawl import LISTING_URL_DEFAULT, scrape_books

FIXTURES = Path(__file__).parent / "fixtures"

D1 = FIXTURES / "detail-1.html"
D2 = FIXTURES / "detail-2.html"

LISTA_MINI = (
    "<article class='product_pod'><h3><a href='detail-1.html' title='A'></a></h3></article>"
    "<article class='product_pod'><h3><a href='detail-2.html' title='B'></a></h3></article>"
).replace("'", '"')


class FakeFetcher:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str) -> str:
        self.calls.append(url)
        return self.pages[url]


def make_fake(**extra) -> tuple[FakeFetcher, str]:
    listing = "http://biblio.test/cat/index.html"
    urls = {urljoin(listing, "detail-1.html"): D1.read_text("utf8"), urljoin(listing, "detail-2.html"): D2.read_text("utf8")}
    pages = {listing: LISTA_MINI, **urls}
    pages.update(extra)
    return FakeFetcher(pages), listing


def test_crawl_happy_entrega_dos_filas_validas():
    fake, listing = make_fake()
    books, invalid = scrape_books(listing, fake, logger=__import__("logging").getLogger())
    assert len(books) == 2
    assert invalid == []
    assert [b.title for b in books] == ["A Light in the Attic", "It's Only the Himalayas"]
    assert books[0].category == "Poetry" and books[1].category == "Travel"
    types_ok = [
        isinstance(b.title, str)
        and isinstance(b.price_number, float)
        and isinstance(b.price_currency, str)
        and isinstance(b.rating, int)
        and isinstance(b.stock, int)
        and isinstance(b.category, str)
        and isinstance(b.url, str)
        for b in books
    ]
    assert all(types_ok)
    # cada columna del CSV castea bien
    assert all(isinstance(getattr(b, "stock"), int) for b in books)


def test_crawl_dedup_una_sola_visita_por_url():
    listing = "http://biblio.test/cat/index.html"
    d1 = D1.read_text("utf8")
    mini = LISTA_MINI.replace(
        "detail-2.html", "detail-1.html"
    )  # segundo artículo apunta al MISMO detalle
    fake = FakeFetcher({listing: mini, "http://biblio.test/cat/detail-1.html": d1})
    books, invalid = scrape_books(listing, fake, logger=__import__("logging").getLogger())
    assert len(books) == 1
    assert invalid == []
    assert len(fake.calls) == 2  # listado + 1 detalle (sin repetir)


def test_crawl_fila_invalida_se_registra_y_no_tumba():
    fake, listing = make_fake()
    roto = D1.read_text("utf8").replace("In stock (22 available)", "In stock")
    fake.pages["http://biblio.test/cat/detail-1.html"] = roto
    books, invalid = scrape_books(listing, fake, logger=__import__("logging").getLogger())
    assert len(books) == 1
    assert len(invalid) == 1
    assert "http://biblio.test/cat/detail-1.html" == invalid[0][0]
    assert "stock" in invalid[0][1] or "campos ausentes" in invalid[0][1]


def test_crawl_max_books():
    fake, listing = make_fake()
    books, _ = scrape_books(
        listing, fake, logger=__import__("logging").getLogger(), max_books=1
    )
    assert len(books) == 1
    assert len(fake.calls) == 2  # listing + 1 detalle


def test_slug_listing_default_es_books_1():
    assert LISTING_URL_DEFAULT.startswith("http://books.toscrape.com/catalogue/category/books_1/")


class ErrorFetcher(FakeFetcher):
    """Fake que lanza HTTPError `code` al pedir `raising_url`."""

    def __init__(self, pages: dict[str, str], raising_url: str, code: int):
        super().__init__(pages)
        self.raising_url = raising_url
        self.code = code

    def get(self, url: str) -> str:
        if url == self.raising_url:
            self.calls.append(url)
            raise urllib.error.HTTPError(url, self.code, "err", None, None)
        return super().get(url)


def test_crawl_404_en_libro_fila_invalida_y_sigue():
    fake, listing = make_fake()
    raising = ErrorFetcher(fake.pages, "http://biblio.test/cat/detail-1.html", 404)
    books, invalid = scrape_books(listing, raising, logger=logging.getLogger())
    assert len(books) == 1
    assert invalid == [("http://biblio.test/cat/detail-1.html", "http 404")]


def test_crawl_403_aborta_la_corrida():
    fake, listing = make_fake()
    raising = ErrorFetcher(fake.pages, "http://biblio.test/cat/detail-1.html", 403)
    with pytest.raises(urllib.error.HTTPError):
        scrape_books(listing, raising, logger=logging.getLogger())
