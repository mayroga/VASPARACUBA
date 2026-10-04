```python
import os
import httpx

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional


app = FastAPI(
    title="Qu-Quieres-Llevar",
    description="Acompañante de preparación de viaje de May Roga LLC",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-1.5-flash"

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)


# ============================================================
# MODELOS
# ============================================================

class ItemCheckRequest(BaseModel):
    item_name: str
    destination: Optional[str] = "Cuba"
    luggage_type: Optional[str] = "mano"


class TripAnalysisRequest(BaseModel):
    origin: str
    destination: str
    flight_type: str
    airline: Optional[str] = "General"


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    La interfaz principal se sirve desde static/index.html
    cuando el despliegue está configurado para servir archivos estáticos.

    Este endpoint solamente confirma que el backend está funcionando.
    """

    return """
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>¿QUÉ QUIERES LLEVAR? | May Roga LLC</title>
    </head>
    <body>
        <h1>¿QUÉ QUIERES LLEVAR?</h1>
        <p>May Roga LLC — servicio online activo.</p>
    </body>
    </html>
    """


# ============================================================
# COMPROBAR ARTÍCULO
# ============================================================

@app.post("/api/check-item")
async def check_item(data: ItemCheckRequest):

    item = data.item_name.strip().lower()

    if not item:
        return {
            "status": "NECESITAMOS SABER QUÉ QUIERES LLEVAR",
            "recommendation": (
                "Escribe el nombre del artículo para poder orientarte."
            ),
            "source": "Orientación May Roga LLC",
        }

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    if GEMINI_API_KEY:

        prompt = f"""
Eres un asistente de preparación de viaje de May Roga LLC.

La persona quiere viajar a {data.destination}.

Artículo consultado:
{data.item_name}

Tipo de equipaje indicado:
{data.luggage_type}

Explica de forma breve, sencilla y humana qué debe revisar antes
de viajar con este artículo.

NO inventes reglas.
NO afirmes que un artículo está permitido o prohibido si no tienes
una fuente oficial que lo confirme.
Distingue entre:
- seguridad aeroportuaria,
- reglas de la aerolínea,
- reglas de entrada al país.

La respuesta debe estar en español.

Empieza utilizando uno de estos estados cuando corresponda:

PUEDES LLEVARLO
PUEDES LLEVARLO, PERO...
NO PUEDES LLEVARLO
REVISA ESTO ANTES DE VIAJAR

Después explica qué debe hacer la persona.
"""

        try:

            async with httpx.AsyncClient(timeout=10.0) as client:

                response = await client.post(
                    GEMINI_URL,
                    params={"key": GEMINI_API_KEY},
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": prompt
                                    }
                                ]
                            }
                        ]
                    },
                )

            if response.status_code == 200:

                result = response.json()

                candidates = result.get("candidates", [])

                if candidates:

                    content = candidates[0].get("content", {})

                    parts = content.get("parts", [])

                    if parts:

                        ai_text = parts[0].get("text", "").strip()

                        if ai_text:

                            return {
                                "status": "REVISA ESTO ANTES DE VIAJAR",
                                "recommendation": ai_text,
                                "source": (
                                    "Orientación asistida por IA. "
                                    "Verifica siempre las fuentes oficiales."
                                ),
                            }

        except Exception:
            # Si Gemini no responde, continúa utilizando
            # las reglas de respaldo.
            pass

    # --------------------------------------------------------
    # REGLAS DE RESPALDO
    # --------------------------------------------------------

    item_normalized = (
        item
        .replace("-", " ")
        .replace("_", " ")
    )

    # Baterías / Power Banks
    if (
        "bateria" in item_normalized
        or "batería" in item_normalized
        or "power bank" in item_normalized
        or "banco de energia" in item_normalized
        or "banco de energía" in item_normalized
    ):

        return {
            "status": "PUEDES LLEVARLO, PERO...",
            "recommendation": (
                "Las baterías de litio y los power banks tienen "
                "restricciones específicas de seguridad. Como regla "
                "general de seguridad aérea, los power banks deben "
                "transportarse en el equipaje de mano y no en el "
                "equipaje documentado. Revisa además las reglas de "
                "tu aerolínea antes de viajar."
            ),
            "source": (
                "Orientación general de seguridad aérea. "
                "Verifica las reglas de tu aerolínea."
            ),
        }

    # Líquidos / Perfumes
    if (
        "perfume" in item_normalized
        or "liquido" in item_normalized
        or "líquido" in item_normalized
        or "crema" in item_normalized
        or "shampoo" in item_normalized
        or "champu" in item_normalized
    ):

        return {
            "status": "PUEDES LLEVARLO, PERO...",
            "recommendation": (
                "Si lo llevas en el equipaje de mano, los líquidos "
                "pueden estar sujetos a límites de cantidad y a las "
                "reglas de seguridad del aeropuerto. Los envases que "
                "superen los límites aplicables normalmente deben "
                "transportarse de otra manera. Revisa las reglas "
                "actuales del aeropuerto y de tu aerolínea antes "
                "de empacar."
            ),
            "source": (
                "Orientación general de seguridad aeroportuaria. "
                "Verifica las reglas oficiales antes de viajar."
            ),
        }

    # --------------------------------------------------------
    # RESPUESTA GENERAL
    # --------------------------------------------------------

    return {
        "status": "REVISA ESTO ANTES DE VIAJAR",
        "recommendation": (
            f"Para el artículo '{data.item_name}', revisa primero "
            "las reglas de seguridad del aeropuerto, las reglas de "
            "equipaje de tu aerolínea y, cuando corresponda, las "
            "reglas oficiales de entrada a tu destino. No asumas "
            "que un artículo está permitido solamente porque "
            "puede caber en tu maleta."
        ),
        "source": "Orientación May Roga LLC",
    }


# ============================================================
# ANÁLISIS BÁSICO DEL VIAJE
# ============================================================

@app.post("/api/analyze-trip")
async def analyze_trip(data: TripAnalysisRequest):

    return {
        "status": "OK",
        "origin": data.origin,
        "destination": data.destination,
        "flight_type": data.flight_type,
        "airline": data.airline,
        "message": (
            "La información del viaje fue recibida. "
            "Verifica siempre vuelos, equipaje, requisitos y "
            "condiciones directamente con las fuentes oficiales "
            "y la aerolínea correspondiente."
        ),
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health_check():

    return {
        "status": "healthy",
        "service": "Qu-Quieres-Llevar online",
        "version": "1.0.0",
        "gemini_configured": bool(GEMINI_API_KEY),
    }
```

Este código ya corrige los errores de sintaxis/indentación y mantiene los endpoints `/api/check-item`, `/api/analyze-trip` y `/api/health`.
