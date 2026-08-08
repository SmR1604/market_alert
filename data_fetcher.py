"""
Descarga precios históricos para una lista de tickers en batch (mucho más rápido
que pedirlos uno por uno) y calcula variaciones porcentuales y volumen relativo.
"""

import logging
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def download_price_history(symbols: list[str], period: str = "3mo") -> dict[str, pd.DataFrame]:
    """
    Descarga histórico de precios para todos los symbols en una sola llamada batch.
    Devuelve un dict {symbol: DataFrame} con columnas Open/High/Low/Close/Volume.
    """
    logger.info("Descargando histórico de precios para %d tickers...", len(symbols))

    raw = yf.download(
        tickers=symbols,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )

    result = {}
    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw
            else:
                df = raw[symbol]
            df = df.dropna(how="all")
            if not df.empty:
                result[symbol] = df
        except (KeyError, TypeError):
            logger.warning("Sin datos para %s, se omite", symbol)

    logger.info("Descarga completa: %d/%d tickers con datos válidos", len(result), len(symbols))
    return result


def compute_change(df: pd.DataFrame, window_days: int) -> float | None:
    """
    % de cambio del precio de cierre entre hace `window_days` sesiones y hoy.
    Devuelve None si no hay suficientes datos.
    """
    if len(df) < window_days + 1:
        return None
    recent_close = df["Close"].iloc[-1]
    past_close = df["Close"].iloc[-(window_days + 1)]
    if past_close == 0 or pd.isna(past_close) or pd.isna(recent_close):
        return None
    return round(((recent_close - past_close) / past_close) * 100, 2)


def compute_volume_ratio(df: pd.DataFrame, lookback_days: int) -> float | None:
    """
    Volumen de la última sesión dividido por el volumen promedio de los `lookback_days`
    anteriores. > 1 significa volumen por encima de lo normal.
    """
    if len(df) < lookback_days + 1:
        return None
    last_volume = df["Volume"].iloc[-1]
    avg_volume = df["Volume"].iloc[-(lookback_days + 1):-1].mean()
    if avg_volume == 0 or pd.isna(avg_volume):
        return None
    return round(last_volume / avg_volume, 2)


def get_current_price(df: pd.DataFrame) -> float:
    return round(float(df["Close"].iloc[-1]), 2)
