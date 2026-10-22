"""Fila canónica del CSV y su esquema de validación."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    title: str
    price_number: float
    price_currency: str
    rating: int
    stock: int
    category: str
    url: str


CSV_COLUMNS = ["title", "price_number", "price_currency", "rating", "stock", "category", "url"]


def validate(book: Book) -> list[str]:
    """Devuelve la lista de errores de esquema; [] significa fila válida."""
    errs: list[str] = []
    if not book.title:
        errs.append("title vacio")
    if not book.price_number or book.price_number <= 0:
        errs.append("precio no positivo")
    if not 1 <= len(book.price_currency) <= 3:
        errs.append("moneda de 1-3 caracteres")
    if not isinstance(book.rating, int) or not 1 <= book.rating <= 5:
        errs.append("rating fuera de 1-5")
    if not isinstance(book.stock, int) or book.stock < 0:
        errs.append("stock no entero o negativo")
    if not book.category:
        errs.append("categoria vacia")
    if not book.url.startswith("http"):
        errs.append("url no absoluta")
    return errs
