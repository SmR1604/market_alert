"""
Configuración central del bot de alertas de mercado.
Todo lo sensible (API keys, credenciales SMTP) se lee desde variables de entorno
para que el mismo código funcione en local y en un servidor 24/7 sin cambios.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Carga variables desde un archivo .env si existe (uso local)

# --- Credenciales / secretos (nunca hardcodear estos valores) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SMTP_HOST = os.getenv("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = os.getenv("SMTP_USER")          # tu correo emisor
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # app password, no tu password normal
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO = os.getenv("EMAIL_TO")            # correo(s) destino, separados por coma

# --- Reglas de detección de señales ---
# Puedes ajustar estos umbrales según qué tan sensible quieres que sea el bot.
DROP_RULES = [
    {"label": "caída_5d", "window_days": 5, "threshold_pct": -10.0},
    {"label": "caída_1m", "window_days": 22, "threshold_pct": -20.0},  # ~22 días hábiles = 1 mes
]

# Spike de volumen: si el volumen de hoy es X veces el promedio de los últimos N días,
# se usa como señal de refuerzo (no obligatoria, pero se incluye en el contexto para la IA)
VOLUME_SPIKE_MULTIPLIER = 2.0
VOLUME_LOOKBACK_DAYS = 20

# --- Proveedor de IA usado para redactar el resumen ---
# "groq"   -> gratis, usa Llama 3.3 70B vía Groq (bueno para probar el proyecto)
# "claude" -> requiere ANTHROPIC_API_KEY de pago, mejor calidad de análisis
AI_PROVIDER = (os.getenv("AI_PROVIDER") or "groq").lower()

CLAUDE_MODEL = "claude-sonnet-5"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"

# --- Control de duplicados ---
# No reenviar alerta del mismo ticker/regla si ya se envió hace menos de N días,
# salvo que la caída haya empeorado significativamente (ver signal_detector.py)
COOLDOWN_DAYS = 3
RE_ALERT_EXTRA_DROP_PCT = 5.0  # si cae 5 puntos porcentuales más, se vuelve a alertar

# --- Archivos de estado (histórico de tickers y alertas ya enviadas) ---
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TICKERS_CACHE_FILE = os.path.join(DATA_DIR, "sp500_tickers.json")
ALERTS_HISTORY_FILE = os.path.join(DATA_DIR, "alerts_history.json")

os.makedirs(DATA_DIR, exist_ok=True)

def validate_config() -> None:
    """
    Verifica que las credenciales mínimas necesarias estén presentes ANTES de
    arrancar el pipeline completo, para fallar rápido con un mensaje claro en
    vez de un traceback críptico a mitad de la ejecución.
    """
    missing = []

    if AI_PROVIDER == "groq" and not GROQ_API_KEY:
        missing.append("GROQ_API_KEY (requerido porque AI_PROVIDER=groq)")
    if AI_PROVIDER == "claude" and not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY (requerido porque AI_PROVIDER=claude)")
    if AI_PROVIDER not in ("groq", "claude"):
        missing.append(f"AI_PROVIDER tiene un valor inválido: '{AI_PROVIDER}' (debe ser 'groq' o 'claude')")

    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not EMAIL_TO:
        missing.append("EMAIL_TO")

    if missing:
        detalle = "\n  - ".join(missing)
        raise RuntimeError(
            f"Faltan variables de entorno / secrets requeridos:\n  - {detalle}\n\n"
            f"Si corres esto en GitHub Actions: revisa Settings → Secrets and "
            f"variables → Actions, y confirma que los NOMBRES coincidan EXACTO "
            f"(sensible a mayúsculas) con los que usa el workflow .github/workflows/daily-check.yml.\n"
            f"Si corres esto en local: revisa tu archivo .env"
        )