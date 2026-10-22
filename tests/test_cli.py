"""Pruebas offline de la CLI (escritores y flags, sin red)."""

import json

from scraper.cli import build_parser, write_csv, write_json
from scraper.models import Book, CSV_COLUMNS

BOOK = Book(
    title="Título ñ y comillas",
    price_number=51.77,
    price_currency="£",
    rating=3,
    stock=22,
    category="Poetry",
    url="http://x.test/u",
)


def test_write_csv_orden_de_columnas(tmp_path):
    salida = tmp_path / "out.csv"
    write_csv([BOOK], str(salida))
    lines = salida.read_text("utf-8").splitlines()
    assert lines[0].split(",") == CSV_COLUMNS
    assert lines[1] == "Título ñ y comillas,51.77,£,3,22,Poetry,http://x.test/u"


def test_write_json_mismas_columnas_ida_vuelta(tmp_path):
    salida = tmp_path / "out.json"
    write_json([BOOK], str(salida))
    data = json.loads(salida.read_text("utf-8"))
    assert list(data[0].keys()) == CSV_COLUMNS
    assert data[0]["title"] == "Título ñ y comillas"
    assert data[0]["price_number"] == 51.77
    assert data[0]["price_currency"] == "£"
    assert data[0]["rating"] == 3
    assert data[0]["stock"] == 22
    assert data[0]["url"] == "http://x.test/u"


def test_flag_format_default_csv_y_json_valido():
    parser = build_parser()
    assert parser.parse_args([]).format == "csv"
    assert parser.parse_args(["--format", "json"]).format == "json"
