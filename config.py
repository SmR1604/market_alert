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

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
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
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()

CLAUDE_MODEL = "claude-sonnet-5"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

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
