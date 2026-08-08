"""
Punto de entrada del bot. Ejecuta el pipeline completo una vez:

  1. Obtiene la lista del S&P 500 (con cache).
  2. Descarga precios históricos en batch.
  3. Detecta señales de caída significativa (config.DROP_RULES).
  4. Genera un resumen con Claude para cada señal.
  5. Envía un email con todo el resumen.

Diseñado para correr como un job periódico (cron local, o cron/systemd timer
en un servidor). Ver README.md para instrucciones de ambos escenarios.
"""

import logging
import sys

from sp500_tickers import get_sp500_tickers
from data_fetcher import download_price_history
from signal_detector import detect_signals
from ai_summarizer import summarize_all
from email_notifier import send_alert_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def run():
    logger.info("=== Iniciando corrida del bot de alertas de mercado ===")

    tickers_meta = get_sp500_tickers()
    symbols = [t["symbol"] for t in tickers_meta]

    price_data = download_price_history(symbols)
    if not price_data:
        logger.error("No se pudo descargar ningún dato de precios. Abortando.")
        sys.exit(1)

    signals = detect_signals(price_data, tickers_meta)

    if not signals:
        logger.info("No hay señales nuevas en esta corrida. Fin.")
        return

    signals_with_summary = summarize_all(signals)
    send_alert_email(signals_with_summary)

    logger.info("=== Corrida finalizada: %d señal(es) procesada(s) ===", len(signals))


if __name__ == "__main__":
    run()
