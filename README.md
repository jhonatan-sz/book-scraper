# book-scraper

Scraper de `books.toscrape.com` (sitio de práctica que permite scraping) que recorre
**todas** las páginas del catálogo (1000 libros en 50 páginas de listado) y entrega un
CSV validado.

Diseño en una línea: **listado descubre URLs → cada página de detalle es la fuente
canónica** (título, precio, rating, stock, categoría). Cero dependencias de runtime
(soLO stdlib).

## requisitos

- Python 3.10+ y [uv](https://docs.astral.sh/uv/) (recomendado) — o solo Python para correr.
- pytest solo si quieres correr los tests (`uv sync --dev` lo instala).

## instalación

```bash
uv sync --dev        # crea .venv (el runtime del scraper no necesita dependencias)
```

## uso

```bash
uv run python -m scraper --out books.csv
```

El mismo comando se puede correr las veces que se quiera: el CSV se regenera completo
y sin duplicados (deduplicación por URL del detalle, que es única en el sitio).

Opciones:

| Opción | Default | ¿Qué hace? |
|---|---|---|
| `--out` | `books.csv` | archivo de salida |
| `--listing-url` | listado completo de la categoría Books | semilla del crawl |
| `--delay` | `0.5` | segundos de espera ENTRE peticiones (cortesía) |
| `--max-books` | sin límite | tope de detalles para pruebas rápidas |

## columnas del CSV

| columna | tipo | ejemplo |
|---|---|---|
| `title` | texto | `A Light in the Attic` |
| `price_number` | float | `51.77` |
| `price_currency` | texto (1–3 chars) | `£` |
| `rating` | entero 1–5 | `3` |
| `stock` | entero ≥ 0 | `22` |
| `category` | texto | `Poetry` |
| `url` | URL absoluta | `http://books.toscrape.com/catalogue/…` |

## cortesía y tolerancia

- `User-Agent` identificable (`book-scraper/0.1 …`) y espera entre peticiones
  (`--delay`; súbelo si el sitio lo pide).
- Reintentos con retroceso exponencial (4 intentos) ante errores transitorios
  (5xx/429/red); 404/403 abortan la petición.
- Una fila inválida se registra en el log y **no tumba** la ejecución.

## esquema y validación

`scraper/models.py` define la fila y `validate()` sus reglas (rating 1–5, precio
positivo, moneda 1–3 caracteres, stock entero ≥ 0, etc.).

## tests (sin red)

```bash
uv run pytest            # o: ./scripts/verify.sh
```

Los tests usan HTML guardado en `tests/fixtures/` (listado p1/p2 + dos páginas de
detalle reales). **No hacen peticiones de red.**

## limitaciones

- Parser determinista para la estructura estable de este sitio (sin JavaScript:
  el HTML servido es el consumido). No es un scraper genérico.
- En la última página el enlace `next` deshabilitado (`href="#"`) se interpreta
  como fin.
- Detalles que cambien de clase CSS (`product_main`, `price_color`, `star-rating`)
  requieren actualizar el parser (los tests de fixtures los detectarían).

## criterios de aceptación (tabla criterio → evidencia)

Ver el mensaje de entrega de esta práctica.
