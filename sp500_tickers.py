"""
Obtiene la lista actual de tickers del S&P 500 desde Wikipedia y la cachea
localmente por 7 días para no golpear la página en cada ejecución.
"""

import json
import time
import logging
import requests
import pandas as pd
from io import StringIO

from config import TICKERS_CACHE_FILE

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 días
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Wikipedia devuelve 403 Forbidden a peticiones sin un User-Agent de navegador
# (el que usa pandas/urllib por defecto es detectado y bloqueado), así que
# descargamos el HTML nosotros mismos con un header adecuado antes de parsear.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def _fetch_from_wikipedia() -> list[dict]:
    """Descarga la tabla de constituyentes del S&P 500 desde Wikipedia."""
    response = requests.get(WIKI_URL, headers=REQUEST_HEADERS, timeout=15)
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))
    df = tables[0]  # la primera tabla es la lista de compañías

    tickers = []
    for _, row in df.iterrows():
        symbol = str(row["Symbol"]).replace(".", "-")  # yfinance usa '-' en vez de '.'
        tickers.append({
            "symbol": symbol,
            "name": str(row["Security"]),
            "sector": str(row.get("GICS Sector", "")),
        })
    return tickers


def get_sp500_tickers(force_refresh: bool = False) -> list[dict]:
    """
    Devuelve la lista de tickers del S&P 500 como lista de dicts:
    [{"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Information Technology"}, ...]
    Usa cache local si está vigente, salvo que force_refresh=True.
    """
    try:
        with open(TICKERS_CACHE_FILE, "r") as f:
            cache = json.load(f)
        if not force_refresh and (time.time() - cache["fetched_at"]) < CACHE_TTL_SECONDS:
            logger.info("Usando lista de tickers cacheada (%d tickers)", len(cache["tickers"]))
            return cache["tickers"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        pass

    logger.info("Descargando lista actualizada del S&P 500 desde Wikipedia...")
    try:
        tickers = _fetch_from_wikipedia()
    except Exception as e:
        logger.error("Fallo al descargar de Wikipedia (%s).", e)
        # Si falla pero hay una cache vieja disponible, mejor usarla que no tener nada
        try:
            with open(TICKERS_CACHE_FILE, "r") as f:
                cache = json.load(f)
            logger.warning("Usando cache vencida como respaldo (%d tickers)", len(cache["tickers"]))
            return cache["tickers"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            raise

    with open(TICKERS_CACHE_FILE, "w") as f:
        json.dump({"fetched_at": time.time(), "tickers": tickers}, f)

    logger.info("Lista actualizada: %d tickers", len(tickers))
    return tickers


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_sp500_tickers(force_refresh=True)
    print(f"Total tickers: {len(data)}")
    print(data[:5])
