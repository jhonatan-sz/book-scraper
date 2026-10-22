from scraper.models import Book, validate


def make_book(**overrides):
    base = dict(
        title="T",
        price_number=10.0,
        price_currency="£",
        rating=3,
        stock=5,
        category="Cat",
        url="http://x/y",
    )
    base.update(overrides)
    return Book(**base)


def test_fila_valida_sin_errores():
    assert validate(make_book()) == []


def test_rating_fuera_de_rango():
    errs = validate(make_book(rating=0))
    assert any("rating" in e for e in errs)
    assert any("rating" in e for e in validate(make_book(rating=6)))


def test_moneda_invalida():
    assert any("moneda" in e for e in validate(make_book(price_currency="GBP!!")))


def test_stock_negativo_y_precio_cero():
    assert any("stock" in e for e in validate(make_book(stock=-1)))
    assert any("precio" in e for e in validate(make_book(price_number=0.0)))


def test_url_relativa_invalida():
    assert any("url" in e for e in validate(make_book(url="/sin-esquema")))
