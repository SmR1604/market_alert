"""
Construye un email HTML con todas las señales del día y lo envía por SMTP.
Funciona con Gmail (usando App Password), Outlook, o cualquier proveedor SMTP.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO

logger = logging.getLogger(__name__)

VEREDICTO_LABELS = {
    "posible_oportunidad": ("🟢", "Posible oportunidad"),
    "cautela": ("🔴", "Señal de cautela"),
    "mixto": ("🟡", "Mixto / revisar con más detalle"),
}


def _build_html(signals: list[dict]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    rows = []

    for s in signals:
        emoji, label = VEREDICTO_LABELS.get(s["veredicto"], ("⚪", "Sin clasificar"))
        rows.append(f"""
        <div style="border:1px solid #e0e0e0; border-radius:8px; padding:16px; margin-bottom:12px;">
          <div style="font-size:16px; font-weight:bold;">
            {emoji} {s['symbol']} — {s['name']}
          </div>
          <div style="color:#555; font-size:13px; margin-bottom:8px;">
            {s['sector']} · {label} · Variación: <b>{s['pct_change']}%</b>
            ({s['window_days']} sesiones) · Precio actual: ${s['current_price']}
            {" · Volumen inusual" if s['volume_spike'] else ""}
          </div>
          <div style="font-size:14px; line-height:1.5;">
            {s['resumen_ia']}
          </div>
        </div>
        """)

    body = "".join(rows) if rows else "<p>No se detectaron señales nuevas hoy.</p>"

    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width:640px; margin:auto;">
        <h2>📊 Resumen de señales de mercado — {today}</h2>
        <p style="color:#777; font-size:13px;">
          Este resumen es generado automáticamente y no constituye asesoría financiera.
          Verifica siempre la información antes de tomar decisiones de inversión.
        </p>
        {body}
      </body>
    </html>
    """


def send_alert_email(signals: list[dict]) -> None:
    if not signals:
        logger.info("No hay señales nuevas, no se envía email.")
        return

    if not all([SMTP_USER, SMTP_PASSWORD, EMAIL_TO]):
        raise RuntimeError(
            "Faltan credenciales de email. Revisa SMTP_USER, SMTP_PASSWORD y EMAIL_TO en tu .env"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 {len(signals)} señal(es) de mercado detectada(s) — {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    msg.attach(MIMEText(_build_html(signals), "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO.split(","), msg.as_string())

    logger.info("Email enviado a %s con %d señal(es)", EMAIL_TO, len(signals))
