import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

app = FastAPI(
    title="¿QUÉ QUIERES LLEVAR? | May Roga LLC",
    description="Acompañamiento independiente para preparación de viajes.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ItemCheckRequest(BaseModel):
    item_name: str
    destination: Optional[str] = "Cuba"
    luggage_type: Optional[str] = "mano"


class TripAnalysisRequest(BaseModel):
    origin: str
    destination: str
    flight_type: str
    airline: Optional[str] = "General"


def local_item_check(item: str, luggage_type: str):
    normalized = (
        item.lower()
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )

    if any(x in normalized for x in [
        "power bank",
        "bateria",
        "batería",
        "pila de litio",
        "banco de energia",
        "banco de energía",
    ]):
        return {
            "status": "PUEDES LLEVARLO, PERO...",
            "recommendation": (
                "Las baterías de litio y los power banks tienen reglas "
                "específicas de seguridad aérea. Como orientación general, "
                "los power banks deben viajar en el equipaje de mano. "
                "Revisa siempre las reglas actuales de tu aerolínea y "
                "del aeropuerto antes de viajar."
            ),
            "source": "Orientación general de seguridad aérea",
        }

    if any(x in normalized for x in [
        "perfume",
        "liquido",
        "líquido",
        "crema",
        "shampoo",
        "champu",
        "champú",
        "colonia",
    ]):
        return {
            "status": "PUEDES LLEVARLO, PERO...",
            "recommendation": (
                "Los líquidos en el equipaje de mano pueden estar sujetos "
                "a límites de cantidad y a controles de seguridad. "
                "Los límites pueden depender del aeropuerto y del tipo "
                "de artículo. Revisa las reglas oficiales antes de empacar."
            ),
            "source": "Orientación general de seguridad aeroportuaria",
        }

    if any(x in normalized for x in [
        "medicamento",
        "medicina",
        "pastilla",
        "medicinas",
    ]):
        return {
            "status": "PUEDES LLEVARLO, PERO...",
            "recommendation": (
                "Los medicamentos pueden estar sujetos a reglas de "
                "seguridad, transporte y entrada al país. Mantén los "
                "medicamentos identificados y lleva contigo la documentación "
                "que corresponda. Verifica las reglas oficiales de tu "
                "aerolínea y destino."
            ),
            "source": "Orientación general de viaje",
        }

    if any(x in normalized for x in [
        "laptop",
        "computadora",
        "ordenador",
        "tablet",
        "ipad",
        "camara",
        "cámara",
    ]):
        return {
            "status": "PUEDES LLEVARLO, PERO...",
            "recommendation": (
                "Los dispositivos electrónicos pueden tener instrucciones "
                "especiales durante el control de seguridad. Es recomendable "
                "llevarlos de forma accesible para poder presentarlos cuando "
                "el personal de seguridad lo solicite. Revisa también las "
                "reglas de tu aerolínea."
            ),
            "source": "Orientación general de seguridad aeroportuaria",
        }

    return {
        "status": "REVISA ESTO ANTES DE VIAJAR",
        "recommendation": (
            f"Para «{item}», revisa tres cosas antes de empacarlo: "
            "las reglas de seguridad del aeropuerto, las reglas de "
            "equipaje de tu aerolínea y, cuando corresponda, las reglas "
            "oficiales de entrada de tu destino. El hecho de que un "
            "artículo quepa en la maleta no significa por sí solo que "
            "pueda transportarse."
        ),
        "source": "Orientación May Roga LLC",
    }


async def ask_gemini(item: str, destination: str, luggage_type: str):
    if not GEMINI_API_KEY:
        return None

    prompt = f"""
Eres el asistente de preparación de viajes de May Roga LLC.

La persona está preparando un viaje a: {destination}.
Artículo consultado: {item}
Tipo de equipaje indicado: {luggage_type}

Da una orientación breve, clara y humana en español.

IMPORTANTE:
- No inventes requisitos.
- No presentes una orientación de IA como una regla oficial.
- No afirmes que algo está permitido o prohibido si no puedes sostenerlo.
- Distingue seguridad aeroportuaria, reglas de la aerolínea y requisitos
  de entrada al país.
- Si depende de la aerolínea, aeropuerto o destino, dilo claramente.
- No solicites contraseñas, datos bancarios ni documentos sensibles.
- No des asesoría legal.
- Termina indicando qué debe verificar la persona.

Comienza con uno de estos estados:
PUEDES LLEVARLO
PUEDES LLEVARLO, PERO...
NO PUEDES LLEVARLO
REVISA ESTO ANTES DE VIAJAR
"""

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ]
                },
            )

        if response.status_code != 200:
            return None

        data = response.json()
        candidates = data.get("candidates") or []

        if not candidates:
            return None

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []

        if not parts:
            return None

        text = parts[0].get("text", "").strip()

        if not text:
            return None

        status = "REVISA ESTO ANTES DE VIAJAR"

        upper = text.upper()

        if "NO PUEDES LLEVARLO" in upper:
            status = "NO PUEDES LLEVARLO"
        elif "PUEDES LLEVARLO, PERO" in upper:
            status = "PUEDES LLEVARLO, PERO..."
        elif "PUEDES LLEVARLO" in upper:
            status = "PUEDES LLEVARLO"

        return {
            "status": status,
            "recommendation": text,
            "source": (
                "Orientación asistida por IA. "
                "Verifica siempre las fuentes oficiales."
            ),
        }

    except Exception:
        return None


@app.get("/", response_class=HTMLResponse)
async def read_root():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)

    return HTMLResponse(
        """
        <!doctype html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>¿QUÉ QUIERES LLEVAR?</title>
        </head>
        <body>
            <h1>¿QUÉ QUIERES LLEVAR?</h1>
            <p>May Roga LLC — servicio online activo.</p>
        </body>
        </html>
        """,
        status_code=200,
    )


@app.post("/api/check-item")
async def check_item(data: ItemCheckRequest):
    item = data.item_name.strip()

    if not item:
        return {
            "status": "NECESITAMOS SABER QUÉ QUIERES LLEVAR",
            "recommendation": (
                "Escribe el nombre del artículo para poder orientarte."
            ),
            "source": "Orientación May Roga LLC",
            "ai_used": False,
        }

    ai_result = await ask_gemini(
        item=item,
        destination=data.destination or "Cuba",
        luggage_type=data.luggage_type or "mano",
    )

    if ai_result:
        ai_result["ai_used"] = True
        return ai_result

    result = local_item_check(
        item=item,
        luggage_type=data.luggage_type or "mano",
    )
    result["ai_used"] = False
    return result


@app.post("/api/analyze-trip")
async def analyze_trip(data: TripAnalysisRequest):
    origin = data.origin.strip()
    destination = data.destination.strip()
    flight_type = data.flight_type.strip()
    airline = (data.airline or "General").strip()

    if not origin or not destination:
        return {
            "status": "FALTA INFORMACIÓN",
            "message": "Indica el origen y el destino de tu viaje.",
        }

    if flight_type.lower() in {"direct", "directo"}:
        flight_message = (
            "Tu viaje está marcado como directo. Aun así, revisa "
            "equipaje, documentos y condiciones directamente con "
            "la aerolínea."
        )
    else:
        flight_message = (
            "Tu viaje tiene una o más escalas. Además de revisar "
            "el destino final, verifica las condiciones de cada "
            "aeropuerto o país de conexión cuando corresponda."
        )

    return {
        "status": "OK",
        "origin": origin,
        "destination": destination,
        "flight_type": flight_type,
        "airline": airline,
        "message": flight_message,
        "next_step": (
            "Compara la información con la aerolínea y las fuentes "
            "oficiales antes de comprar o viajar."
        ),
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Qu-Quieres-Llevar online",
        "version": "2.0.0",
        "gemini_configured": bool(GEMINI_API_KEY),
    }
