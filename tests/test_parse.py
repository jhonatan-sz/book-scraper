from pathlib import Path

import pytest

from scraper.parse import _split_price, parse_detail, parse_listing

FIXTURES = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_listado_p1_extrae_20_y_siguiente():
    hrefs, next_href, total = parse_listing(read("listing-p1.html"))
    assert len(hrefs) == 20
    assert next_href == "page-2.html"
    assert total == 50
    assert "a-light-in-the-attic_1000" in hrefs[0]


def test_listado_p2_extrae_20_y_siguiente_es_p3():
    hrefs, next_href, total = parse_listing(read("listing-p2.html"))
    assert len(hrefs) == 20
    assert next_href == "page-3.html"
    assert total == 50


def test_detalle_1_campos_canonicos():
    book = parse_detail(read("detail-1.html"), "http://libro.test/d1")
    assert book.title == "A Light in the Attic"
    assert book.price_number == 51.77
    assert book.price_currency == "£"
    assert book.rating == 3
    assert book.stock == 22
    assert book.category == "Poetry"
    assert book.url == "http://libro.test/d1"


def test_detalle_2_campos_canonicos():
    book = parse_detail(read("detail-2.html"), "http://libro.test/d2")
    assert book.title == "It's Only the Himalayas"
    assert book.price_number == 45.17
    assert book.price_currency == "£"
    assert book.rating == 2
    assert book.stock == 19
    assert book.category == "Travel"


def test_precio_parte_moneda_y_numero():
    assert _split_price("£51.77") == (51.77, "£")
    assert _split_price("£1,234.00") == (1234.0, "£")
    with pytest.raises(ValueError, match="ilegible"):
        _split_price("sin numero")


def test_detalle_sin_stock_invalido():
    broken = read("detail-1.html").replace("In stock (22 available)", "In stock")
    with pytest.raises(ValueError, match="stock"):
        parse_detail(broken, "http://libro.test/roto")


def test_detalle_sin_breadcrumb_invalido():
    broken = read("detail-1.html").replace("breadcrumb", "otra-cosa")
    with pytest.raises(ValueError, match="breadcrumb"):
        parse_detail(broken, "http://libro.test/roto")
