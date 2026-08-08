"""
Por cada señal detectada:
1. Obtiene contexto adicional (fundamentales básicos + titulares recientes) vía yfinance.
   Esto solo se hace para los tickers que YA dispararon una señal (pocos), no para
   los 500, así que el costo de estas llamadas más lentas es marginal.
2. Le pasa ese contexto a un modelo de IA para que redacte un resumen breve en español,
   con un veredicto: "posible oportunidad" vs "señal de alerta / cuidado".

Soporta dos proveedores intercambiables vía config.AI_PROVIDER:
  - "groq"   -> gratis, usa Llama 3.3 70B (bueno para probar el proyecto sin costo)
  - "claude" -> usa la API de Anthropic, mejor calidad de análisis, tiene costo

El cambio entre uno y otro es solo una variable de entorno (AI_PROVIDER en .env),
no hay que tocar el resto del pipeline.
"""

import json
import logging
import yfinance as yf

from config import AI_PROVIDER, ANTHROPIC_API_KEY, CLAUDE_MODEL, GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un analista financiero que redacta resúmenes breves y objetivos \
sobre movimientos de acciones para un boletín de alertas personal (no un producto público, \
no hay obligación regulatoria de disclaimers extensos, pero sé honesto sobre incertidumbre).

Reglas estrictas:
- Nunca uses lenguaje de "recomendación de compra" categórica (evita "compra ahora", "es un hecho").
- Explica EN QUÉ CONTEXTO ocurrió la caída usando los datos entregados (noticias, sector, fundamentales).
- Distingue explícitamente entre dos escenarios: (a) posible sobreventa/oportunidad técnica \
sin deterioro aparente del negocio, o (b) señales de deterioro real (ej. resultados débiles, \
recorte de guías, problemas legales, etc.) que ameritan cautela.
- Sé conciso: 3-4 oraciones máximo.
- Responde SIEMPRE en español neutro.
- Devuelve SOLO un objeto JSON válido, sin texto adicional, con este formato exacto:
{"veredicto": "posible_oportunidad" | "cautela" | "mixto", "resumen": "..."}
"""


def _get_extra_context(symbol: str) -> dict:
    """Fundamentales básicos + titulares recientes desde yfinance (best-effort)."""
    context = {"pe_ratio": None, "market_cap": None, "recent_news": []}
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        context["pe_ratio"] = info.get("trailingPE")
        context["market_cap"] = info.get("marketCap")
        context["fifty_two_week_low"] = info.get("fiftyTwoWeekLow")
        context["fifty_two_week_high"] = info.get("fiftyTwoWeekHigh")

        news_items = ticker.news or []
        context["recent_news"] = [
            item.get("title", "") for item in news_items[:5] if item.get("title")
        ]
    except Exception as e:
        logger.warning("No se pudo obtener contexto extra para %s: %s", symbol, e)
    return context


def _build_user_prompt(signal: dict, extra: dict) -> str:
    return f"""Analiza esta señal de mercado y redacta el resumen según las reglas:

Ticker: {signal['symbol']} ({signal['name']})
Sector: {signal['sector']}
Variación: {signal['pct_change']}% en {signal['window_days']} sesiones
Precio actual: ${signal['current_price']}
Volumen inusual (spike): {"sí" if signal['volume_spike'] else "no"}
P/E ratio: {extra.get('pe_ratio')}
Mínimo/Máximo 52 semanas: {extra.get('fifty_two_week_low')} / {extra.get('fifty_two_week_high')}
Titulares recientes: {extra.get('recent_news') or "sin titulares recientes disponibles"}
"""


def _call_claude(user_prompt: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()


def _call_groq(user_prompt: str) -> str:
    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=400,
        response_format={"type": "json_object"},  # fuerza salida JSON válida
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def summarize_signal(signal: dict) -> dict:
    """
    Recibe una señal de signal_detector.py, la enriquece con contexto y llama al
    proveedor de IA configurado. Devuelve la señal original con dos campos nuevos:
    'veredicto' y 'resumen_ia'.
    """
    extra = _get_extra_context(signal["symbol"])
    user_prompt = _build_user_prompt(signal, extra)

    try:
        if AI_PROVIDER == "groq":
            text = _call_groq(user_prompt)
        elif AI_PROVIDER == "claude":
            text = _call_claude(user_prompt)
        else:
            raise ValueError(f"AI_PROVIDER desconocido: '{AI_PROVIDER}' (usa 'groq' o 'claude')")

        parsed = json.loads(text)
        signal["veredicto"] = parsed.get("veredicto", "mixto")
        signal["resumen_ia"] = parsed.get("resumen", "No se pudo generar el resumen.")
    except Exception as e:
        logger.error("Error generando resumen (%s) para %s: %s", AI_PROVIDER, signal["symbol"], e)
        signal["veredicto"] = "mixto"
        signal["resumen_ia"] = (
            f"No se pudo generar el análisis automático ({e}). "
            f"Revisa el ticker manualmente antes de decidir."
        )

    return signal


def summarize_all(signals: list[dict]) -> list[dict]:
    return [summarize_signal(s) for s in signals]
