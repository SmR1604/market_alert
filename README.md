# Market Alert Bot

Bot que monitorea el S&P 500, detecta caídas significativas de precio, y envía
un email con un resumen generado por IA de cada posible oportunidad o señal
de cautela.

## ⚠️ Importante

Esto **no es asesoría financiera**. Es una herramienta de detección de señales
basada en reglas simples (% de caída). Una caída fuerte puede ser una oportunidad
de compra o puede ser el inicio de un deterioro real del negocio — el resumen de
la IA te da contexto, pero la decisión final de invertir es siempre tuya.

## 1. Instalación local

```bash
cd market_alert_bot
python3 -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurar credenciales

```bash
cp .env.example .env
```

Edita `.env` y completa:

- **AI_PROVIDER**: `groq` (gratis, por defecto) o `claude` (de pago, mejor calidad)
- **GROQ_API_KEY** (si usas `groq`): gratis, sin tarjeta de crédito, en
  https://console.groq.com/keys — inicia sesión, click en "Create API Key", listo
- **ANTHROPIC_API_KEY** (solo si usas `claude`): la sacas en
  https://console.anthropic.com/settings/keys
- **SMTP_USER / SMTP_PASSWORD**: si usas Gmail, necesitas generar una
  "Contraseña de aplicación" (no tu password normal):
  https://myaccount.google.com/apppasswords
- **EMAIL_TO**: a qué correo(s) llegan las alertas (puedes poner el mismo que SMTP_USER)

### Sobre el modo gratis (Groq)

Groq usa Llama 3.3 70B en vez de Claude. Es gratis y sin tarjeta, pero:
- El tier gratis tiene límites de tokens/minuto y requests/día (de sobra para probar,
  pero si tu bot detecta muchas señales de golpe en una corrida puede toparse con el límite)
- La calidad del análisis es buena pero algo menos matizada que Claude
- Cuando quieras pasar a producción real, cambia `AI_PROVIDER=claude` en tu `.env`
  y no hay que tocar nada más del código

## 3. Ejecutar manualmente (para probar)

```bash
python main.py
```

La primera vez descarga la lista completa del S&P 500 (tarda ~1-2 min en
bajar los precios de ~500 tickers). Si no hay señales, no se envía ningún
correo — es normal, significa que no hay caídas que superen los umbrales.

Puedes ajustar qué tan sensible es la detección en `config.py`, sección
`DROP_RULES`. Por defecto:
- Caída de 10% o más en 5 sesiones
- Caída de 20% o más en ~1 mes (22 sesiones)

## 4. Automatizar en tu computadora (cron / Task Scheduler)

**Linux/Mac (cron)** — para correr todos los días a las 18:00 (después del
cierre del mercado en EE.UU.):

```bash
crontab -e
```

Agrega (ajusta las rutas a las tuyas):
```
0 18 * * 1-5 cd /ruta/a/market_alert_bot && /ruta/a/venv/bin/python main.py >> logs.txt 2>&1
```

**Windows (Task Scheduler)**: crea una tarea programada que ejecute
`venv\Scripts\python.exe main.py` con "Iniciar en" apuntando a la carpeta
del proyecto, de lunes a viernes a la hora que prefieras.

## 5. Desplegarlo gratis y 24/7 con GitHub Actions

GitHub Actions te deja correr este bot todos los días automáticamente, sin
servidor propio, sin tarjeta de crédito, y con las credenciales guardadas
de forma segura (encriptadas, nunca visibles en el código ni en los logs).

### Paso 1: Crear el repositorio

```bash
cd market_alert_bot
git init
git add .
git commit -m "Primer commit del bot de alertas"
```

Crea un repositorio nuevo en https://github.com/new (puede ser privado o
público — con privado igual tienes 2.000 minutos gratis al mes, más que
suficiente para una corrida diaria de ~2-3 minutos). Luego:

```bash
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git branch -M main
git push -u origin main
```

### Paso 2: Configurar los Secrets (credenciales)

En tu repositorio en GitHub: **Settings → Secrets and variables → Actions →
New repository secret**. Agrega cada uno de estos:

| Secret | Valor |
|---|---|
| `AI_PROVIDER` | `groq` |
| `GROQ_API_KEY` | tu key de https://console.groq.com/keys |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | tu correo |
| `SMTP_PASSWORD` | tu App Password de Gmail |
| `EMAIL_FROM` | tu correo |
| `EMAIL_TO` | a quién le llega la alerta |

(Si más adelante quieres usar Claude en vez de Groq, agrega también el
secret `ANTHROPIC_API_KEY` y cambia `AI_PROVIDER` a `claude`.)

### Paso 3: Listo — ya está programado

El archivo `.github/workflows/daily-check.yml` ya viene configurado para
correr de lunes a viernes a las 22:30 UTC (ajusta el cron a tu gusto —
GitHub Actions siempre usa UTC, no tu zona horaria local).

Para probarlo ahora mismo sin esperar al horario programado: en GitHub ve a
la pestaña **Actions → Market Alert Bot - Corrida diaria → Run workflow**.

El workflow guarda automáticamente el historial de alertas de vuelta al
repositorio (carpeta `data/`) después de cada corrida, para no repetirte
la misma alerta al día siguiente.

### Notas sobre este método

- Los horarios de `schedule` en GitHub Actions pueden atrasarse 10-30 min
  en horas pico — no es problema para este caso de uso (no es time-critical)
- Si el repositorio queda 60 días sin ninguna actividad, GitHub desactiva
  el cron automáticamente (poco probable si vas revisando los emails)
- Puedes ver el log completo de cada corrida en la pestaña **Actions**,
  muy útil para debuggear si algo falla

## 6. Estructura del proyecto

```
market_alert_bot/
├── .github/workflows/
│   └── daily-check.yml    # Programa la corrida diaria en GitHub Actions (gratis)
├── config.py               # Umbrales, credenciales (vía .env), reglas
├── sp500_tickers.py        # Descarga y cachea la lista del S&P 500
├── data_fetcher.py         # Descarga precios históricos en batch (yfinance)
├── signal_detector.py      # Aplica las reglas y evita alertas duplicadas
├── ai_summarizer.py        # Llama a Groq/Claude para redactar el resumen + veredicto
├── email_notifier.py       # Construye y envía el email HTML
├── main.py                 # Orquesta todo el pipeline
├── data/                   # Cache de tickers + historial de alertas (se crea solo)
├── requirements.txt
├── .gitignore
└── .env.example
```

## 7. Errores comunes

- **HTTP 403 Forbidden al descargar de Wikipedia**: ya solucionado en el código
  (Wikipedia bloquea peticiones sin un User-Agent de navegador). Si vuelve a pasar,
  puede ser que Wikipedia haya cambiado la estructura de la página — avísame.
- **Rate limit de yfinance**: si corres el script muchas veces seguidas en poco
  tiempo, Yahoo Finance puede bloquear temporalmente tu IP. Espera unos minutos.
- **SMTPAuthenticationError**: revisa que estés usando una "Contraseña de aplicación"
  de Gmail y no tu contraseña normal (Gmail requiere tener verificación en 2 pasos
  activada para poder generar una).

## 8. Próximos pasos posibles

- Agregar más reglas de detección (RSI, ruptura de medias móviles, etc.) en `signal_detector.py`
- Cambiar el canal de notificación (Telegram, Slack) — solo hay que reemplazar `email_notifier.py`
- Guardar histórico en una base de datos (Postgres) en vez de JSON, si el volumen crece
- Exponer un pequeño dashboard web (FastAPI) para ver el historial de señales
