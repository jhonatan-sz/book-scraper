"""Cliente HTTP mínimo (stdlib): UA identificable, paso entre peticiones y reintentos."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

USER_AGENT = "book-scraper/0.1 (practica; books.toscrape.com permite el scraping)"
DEFAULT_DELAY = 0.5
DEFAULT_RETRIES = 4
DEFAULT_TIMEOUT = 30

# errores que SÍ reintentan (transitorios); 4xx de permisos/ausencia no
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class Fetcher:
    """Descarga HTML con cortesía: espera `delay` entre peticiones y reintenta con retroceso."""

    def __init__(
        self,
        delay: float = DEFAULT_DELAY,
        retries: int = DEFAULT_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self._last_request: float | None = None

    def get(self, url: str) -> str:
        """Devuelve el HTML como texto; RuntimeError si se agotan los intentos."""
        if self._last_request is not None and self.delay > 0:
            wait = self._last_request + self.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)

        last_error: Exception | None = None
        for attempt in range(self.retries):
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    self._last_request = time.monotonic()
                    if resp.status != 200:
                        raise urllib.error.HTTPError(
                            url, resp.status, "codigo no 200", resp.headers, None
                        )
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                self._last_request = time.monotonic()
                if exc.code not in _RETRYABLE_STATUS:
                    raise
                last_error = exc
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
                self._last_request = time.monotonic()
                last_error = exc
            time.sleep(min(2.0**attempt, 8.0))  # retroceso exponencial acotado

        raise RuntimeError(
            f"no se pudo descargar {url} tras {self.retries} intentos: {last_error}"
        )
