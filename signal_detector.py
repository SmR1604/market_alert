"""
Aplica las reglas de config.DROP_RULES sobre los datos descargados y decide
qué tickers constituyen una señal nueva (evitando reenviar la misma alerta
dentro del período de cooldown, salvo que la caída haya empeorado).
"""

import json
import logging
import time
from datetime import datetime, timezone

from config import (
    DROP_RULES,
    VOLUME_SPIKE_MULTIPLIER,
    VOLUME_LOOKBACK_DAYS,
    COOLDOWN_DAYS,
    RE_ALERT_EXTRA_DROP_PCT,
    ALERTS_HISTORY_FILE,
)
from data_fetcher import compute_change, compute_volume_ratio, get_current_price

logger = logging.getLogger(__name__)


def _load_history() -> dict:
    try:
        with open(ALERTS_HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_history(history: dict) -> None:
    with open(ALERTS_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def _should_alert(history: dict, symbol: str, rule_label: str, current_pct: float) -> bool:
    """Decide si corresponde alertar según cooldown y empeoramiento de la caída."""
    key = f"{symbol}:{rule_label}"
    prev = history.get(key)
    if prev is None:
        return True

    days_since = (time.time() - prev["timestamp"]) / 86400
    if days_since >= COOLDOWN_DAYS:
        return True

    # Si la caída empeoró significativamente respecto a la última alerta, sí reavisamos
    if current_pct <= prev["pct"] - RE_ALERT_EXTRA_DROP_PCT:
        return True

    return False


def detect_signals(price_data: dict, tickers_meta: list[dict]) -> list[dict]:
    """
    price_data: {symbol: DataFrame} ya descargado por data_fetcher.
    tickers_meta: lista de dicts con symbol/name/sector (de sp500_tickers.py).
    Devuelve una lista de señales nuevas a alertar, cada una con todo el contexto
    necesario para pasarle a la IA y para el email.
    """
    meta_by_symbol = {t["symbol"]: t for t in tickers_meta}
    history = _load_history()
    signals = []

    for symbol, df in price_data.items():
        for rule in DROP_RULES:
            pct_change = compute_change(df, rule["window_days"])
            if pct_change is None or pct_change > rule["threshold_pct"]:
                continue  # no cumple el umbral de caída de esta regla

            if not _should_alert(history, symbol, rule["label"], pct_change):
                logger.info("%s (%s) en cooldown, se omite", symbol, rule["label"])
                continue

            volume_ratio = compute_volume_ratio(df, VOLUME_LOOKBACK_DAYS)
            signals.append({
                "symbol": symbol,
                "name": meta_by_symbol.get(symbol, {}).get("name", symbol),
                "sector": meta_by_symbol.get(symbol, {}).get("sector", "N/D"),
                "rule_label": rule["label"],
                "window_days": rule["window_days"],
                "pct_change": pct_change,
                "current_price": get_current_price(df),
                "volume_spike": bool(volume_ratio and volume_ratio >= VOLUME_SPIKE_MULTIPLIER),
                "volume_ratio": volume_ratio,
            })

            # Actualizamos el historial inmediatamente para no duplicar en la misma corrida
            history[f"{symbol}:{rule['label']}"] = {
                "pct": pct_change,
                "timestamp": time.time(),
                "date": datetime.now(timezone.utc).isoformat(),
            }

    _save_history(history)
    logger.info("Señales nuevas detectadas: %d", len(signals))
    return signals
