# book-scraper

**Demo project on a practice site** (`books.toscrape.com`): muestra hecha sobre un
sitio de práctica que permite scraping — no es entrega para un cliente. Recorre
**todas** las páginas del catálogo (1000 libros en 50 páginas de listado) y entrega un
CSV (o JSON) validado.

Diseño en una línea: **el listado descubre URLs → cada página de detalle es la fuente
canónica** (título, precio, rating, stock, categoría). Cero dependencias de runtime
(solo stdlib).

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
uv run python -m scraper --out books.json --format json   # salida JSON, mismas columnas
```

El mismo comando se puede correr las veces que se quiera: el CSV se regenera completo
y sin duplicados (deduplicación por URL del detalle, que es única en el sitio).

Opciones:

| Opción | Default | ¿Qué hace? |
|---|---|---|
| `--out` | `books.csv` | archivo de salida |
| `--listing-url` | listado completo de la categoría Books | semilla del crawl |
| `--delay` | `0.5` | segundos de espera entre peticiones (cortesía) |
| `--max-books` | sin límite | tope de detalles para pruebas rápidas |
| `--format` | `csv` | formato de salida (`csv` o `json`, mismas columnas) |

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
  (5xx/429/red); un 404 en un libro se registra como fila inválida y el crawl
  sigue; 403 y demás 4xx abortan la corrida (protege de bloqueos).
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

- Parser: `html.parser` de la stdlib, dirigido al markup estable de ESTE sitio (sin
  JavaScript: el HTML servido es el consumido). No es un scraper genérico.
- `price_number` es `float` (en memoria es el precio como céntimos sería más
  correcto; el CSV/JSON lo expone con dos decimales tal como llega).
- En la última página el enlace `next` deshabilitado (`href="#"`) se interpreta
  como fin.
- Cambios de clases CSS del sitio (`product_main`, `price_color`, `star-rating`)
  requieren actualizar el parser (los tests de fixtures los detectarían).

## nota de calidad de dato (hallada por la validación)

El sitio tiene una categoría con nombre extraño: `Add a comment`
(`category/books/add-a-comment_18/`, listada en la propia nav del sitio). 67 libros
viven ahí con su breadcrumb `Home > Books > Add a comment > título` bien formado.
**El scraper no corrige datos de origen: reporta la categoría tal cual** y este README
lo documenta. Si el cliente pide renombrarla, es una línea de post-proceso aparte.

## criterios de aceptación (tabla criterio → evidencia)

| # | criterio | resultado | evidencia |
|---|---|---|---|
| 1 | filas == realidad del sitio | ✅ 1000/1000 | log real: `RESULT filas=1000 invalidas=0` (50 páginas × 20) |
| 2 | repetible sin duplicados | ✅ | corrida #1 y #2 → mismo sha256; `sort \| uniq -d` = 0 líneas (re-certificado en terminal del operador, 2026-10-22: mismo hash + `dirty-diff` `e3b0c44298fc`) |
| 3 | tipos correctos en todas las columnas | ✅ | chequeo full-dataset: 0 errores de tipo (float/int en 1000 filas) |
| 4 | clon limpio + README | ✅ | `git clone` → `verify.sh` (passed, VERIFY OK) → crawl smoke `filas=2` |
| 5 | tests + verify exit 0 | ✅ | tests offline (fixtures HTML reales, sin red) + `VERIFY OK` en recibo |

Los CSV de evidencia (run1/run2) salieron de la versión regex del parser; tras el
refactor a `html.parser` (5d1caf7) un smoke real de 2 libros produjo **filas
idénticas** a las de run1 (`diff` sobre header + 2 filas). Tests: 17 al momento de
los runs; 22 tras añadir 404/JSON.

(corridas: #1 `776.9s` y #2 `791.8s` con delay por defecto `0.5s`; `diff` entre
ambos CSV: **IDÉNTICAS**; sha256 compartido `b00019e42c1dcf4b…`.)
