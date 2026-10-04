import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


VERSION = "4.0.0"
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

app = FastAPI(
    title="¿QUÉ QUIERES LLEVAR? | May Roga LLC",
    description="Preparación independiente para viajar.",
    version=VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )


class ItemCheckRequest(BaseModel):
    item_name: str
    destination: Optional[str] = "Cuba"
    luggage_type: Optional[str] = "mano"


class TripAnalysisRequest(BaseModel):
    origin: str
    destination: str
    flight_type: str
    airline: Optional[str] = "General"
    date: Optional[str] = ""
    passengers: Optional[str] = "1"
    has_stops: Optional[str] = "direct"
    stop_location: Optional[str] = ""


class GeminiRequest(BaseModel):
    prompt: str
    destination: Optional[str] = "Cuba"


def normalize(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
    )


def result(status, recommendation, source, ai_used=False):
    return {
        "status": status,
        "recommendation": recommendation,
        "source": source,
        "ai_used": ai_used,
    }


def local_item_check(item_name, destination="Cuba", luggage_type="mano"):
    item = normalize(item_name)

    if not item:
        return result(
            "NECESITAMOS SABER QUÉ QUIERES LLEVAR",
            "Escribe el nombre del artículo para poder orientarte.",
            "Orientación May Roga LLC",
        )

    if any(x in item for x in [
        "power bank",
        "bateria",
        "batería",
        "baterias",
        "baterías",
        "pila de litio",
        "banco de energia",
        "banco de energía",
    ]):
        return result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Las baterías de litio y los power banks tienen reglas "
                "específicas de seguridad aérea. Como orientación general, "
                "los power banks deben transportarse en el equipaje de mano. "
                "Confirma siempre las reglas actuales de tu aerolínea y "
                "aeropuerto antes de viajar."
            ),
            "Orientación general de seguridad aérea",
        )

    if any(x in item for x in [
        "perfume",
        "liquido",
        "líquido",
        "crema",
        "shampoo",
        "champu",
        "champú",
        "colonia",
    ]):
        return result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Los líquidos pueden estar sujetos a límites y controles "
                "de seguridad cuando se llevan en el equipaje de mano. "
                "Revisa las reglas vigentes del aeropuerto y de tu "
                "aerolínea antes de empacar."
            ),
            "Orientación general de seguridad aeroportuaria",
        )

    if any(x in item for x in [
        "medicamento",
        "medicina",
        "medicinas",
        "pastilla",
    ]):
        return result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Los medicamentos pueden tener reglas especiales de "
                "transporte y también pueden existir requisitos del país "
                "de destino. Revisa las reglas oficiales antes de viajar."
            ),
            "Orientación general de viaje",
        )

    if any(x in item for x in [
        "laptop",
        "computadora",
        "ordenador",
        "tablet",
        "ipad",
        "camara",
        "cámara",
    ]):
        return result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Los dispositivos electrónicos pueden requerir atención "
                "durante el control de seguridad. Llévalos de forma "
                "accesible y sigue las instrucciones del personal de "
                "seguridad y de tu aerolínea."
            ),
            "Orientación general de seguridad aeroportuaria",
        )

    return result(
        "REVISA ESTO ANTES DE VIAJAR",
        (
            f"Para «{item_name}», revisa las reglas de seguridad del "
            "aeropuerto, las condiciones de equipaje de tu aerolínea y, "
            f"cuando corresponda, las reglas oficiales de entrada de "
            f"{destination}. Confirma la información antes de empacarlo."
        ),
        "Orientación May Roga LLC",
    )


async def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
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

        return text or None

    except Exception:
        return None


def detect_status(text):
    upper = text.upper()

    if "NO PUEDES LLEVARLO" in upper:
        return "NO PUEDES LLEVARLO"

    if "PUEDES LLEVARLO, PERO" in upper:
        return "PUEDES LLEVARLO, PERO..."

    if "PUEDES LLEVARLO" in upper:
        return "PUEDES LLEVARLO"

    return "REVISA ESTO ANTES DE VIAJAR"


@app.get("/")
async def home():
    if INDEX_FILE.is_file():
        return FileResponse(
            str(INDEX_FILE),
            media_type="text/html",
        )

    return HTMLResponse(
        """
        <!doctype html>
        <html lang="es">
        <head>
        <meta charset="utf-8">
        <meta name="viewport"
              content="width=device-width,initial-scale=1">
        <title>¿QUÉ QUIERES LLEVAR? | May Roga LLC</title>
        </head>
        <body>
        <h1>¿QUÉ QUIERES LLEVAR?</h1>
        <p>May Roga LLC</p>
        <p>
        No se encontró el archivo static/index.html.
        </p>
        </body>
        </html>
        """,
        status_code=200,
    )


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "Qu-Quieres-Llevar",
        "company": "May Roga LLC",
        "version": VERSION,
        "gemini_configured": bool(GEMINI_API_KEY),
        "index_exists": INDEX_FILE.is_file(),
        "static_exists": STATIC_DIR.exists(),
    }


@app.get("/api")
async def api_info():
    return {
        "status": "online",
        "name": "¿QUÉ QUIERES LLEVAR?",
        "company": "May Roga LLC",
        "version": VERSION,
        "endpoints": [
            "/api/health",
            "/api/check-item",
            "/api/analyze-trip",
            "/api/trip",
            "/api/gemini",
            "/api/dviajeros",
            "/api/evisa",
            "/api/airlines",
            "/api/config",
        ],
    }


@app.post("/api/check-item")
async def check_item(data: ItemCheckRequest):
    item = data.item_name.strip()
    destination = (data.destination or "Cuba").strip()
    luggage = (data.luggage_type or "mano").strip()

    if not item:
        return result(
            "NECESITAMOS SABER QUÉ QUIERES LLEVAR",
            "Escribe el nombre del artículo para poder orientarte.",
            "Orientación May Roga LLC",
        )

    prompt = f"""
Eres el asistente de preparación de viajes de May Roga LLC.

Destino:
{destination}

Artículo:
{item}

Equipaje:
{luggage}

Responde en español, de forma sencilla y humana.

No eres una aerolínea, aeropuerto, gobierno,
aduana ni autoridad migratoria.

No inventes requisitos.
No inventes límites.
No afirmes que una regla está oficialmente verificada
si no existe una fuente oficial disponible.

Distingue entre:
- seguridad aeroportuaria,
- reglas de la aerolínea,
- reglas de entrada al destino.

Usa uno de estos estados:

PUEDES LLEVARLO
PUEDES LLEVARLO, PERO...
NO PUEDES LLEVARLO
REVISA ESTO ANTES DE VIAJAR

Después explica qué debe revisar la persona.
"""

    ai_text = await ask_gemini(prompt)

    if ai_text:
        return result(
            detect_status(ai_text),
            ai_text,
            (
                "Orientación asistida por IA. "
                "Verifica siempre las fuentes oficiales."
            ),
            True,
        )

    return local_item_check(
        item,
        destination,
        luggage,
    )


@app.post("/api/analyze-trip")
async def analyze_trip(data: TripAnalysisRequest):
    origin = data.origin.strip()
    destination = data.destination.strip()

    if not origin or not destination:
        return JSONResponse(
            status_code=400,
            content={
                "status": "FALTA INFORMACIÓN",
                "message": (
                    "Indica el origen y el destino "
                    "para continuar."
                ),
            },
        )

    if data.has_stops == "stops":
        message = (
            "Tu viaje tiene una o más escalas. "
            "Revisa también las condiciones de las conexiones."
        )
    else:
        message = (
            "Tu viaje está marcado como directo. "
            "Revisa igualmente los documentos y el equipaje."
        )

    return {
        "status": "OK",
        "origin": origin,
        "destination": destination,
        "date": data.date or "",
        "passengers": data.passengers or "1",
        "flight_type": data.flight_type,
        "airline": data.airline or "General",
        "has_stops": data.has_stops or "direct",
        "stop_location": data.stop_location or "",
        "message": message,
    }


@app.post("/api/trip")
async def save_trip(data: TripAnalysisRequest):
    return {
        "status": "OK",
        "trip": {
            "origin": data.origin,
            "destination": data.destination,
            "date": data.date or "",
            "passengers": data.passengers or "1",
            "flight_type": data.flight_type,
            "airline": data.airline or "General",
            "has_stops": data.has_stops or "direct",
            "stop_location": data.stop_location or "",
        },
        "message": "Información del viaje recibida correctamente.",
    }


@app.post("/api/gemini")
async def gemini_proxy(data: GeminiRequest):
    prompt = data.prompt.strip()

    if not prompt:
        return JSONResponse(
            status_code=400,
            content={
                "status": "ERROR",
                "message": "No se recibió ninguna consulta.",
            },
        )

    full_prompt = f"""
Eres un asistente de preparación de viajes de May Roga LLC.

Destino:
{data.destination or "Cuba"}

La aplicación es independiente.
No es una aerolínea, agencia de viajes,
gobierno, aeropuerto ni autoridad migratoria.

No inventes requisitos.
No inventes reglas.
No afirmes verificaciones que no hayas realizado.

Consulta:
{prompt}
"""

    text = await ask_gemini(full_prompt)

    if not text:
        return {
            "status": "UNAVAILABLE",
            "message": (
                "La orientación automática no está disponible "
                "en este momento."
            ),
        }

    return {
        "status": "OK",
        "text": text,
        "source": (
            "Orientación asistida por IA. "
            "Verifica la información en la fuente oficial."
        ),
    }


@app.get("/api/config")
async def config():
    return {
        "gemini_available": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL if GEMINI_API_KEY else None,
    }


@app.get("/api/dviajeros")
async def dviajeros():
    return {
        "status": "OK",
        "title": "Simulación D’Viajeros",
        "official_site": "https://dviajeros.mitrans.gob.cu/",
        "message": (
            "Esta es una práctica educativa. "
            "No sustituye el formulario oficial."
        ),
    }


@app.get("/api/evisa")
async def evisa():
    return {
        "status": "OK",
        "title": "eVisa Cuba",
        "official_site": "https://evisacuba.cu/",
        "message": (
            "Consulta siempre el portal oficial "
            "para el proceso vigente."
        ),
    }


@app.get("/api/airlines")
async def airlines():
    return {
        "status": "OK",
        "airlines": [
            {
                "name": "American Airlines",
                "official": "https://www.aa.com/",
            },
            {
                "name": "Delta Air Lines",
                "official": "https://www.delta.com/",
            },
            {
                "name": "Southwest Airlines",
                "official": "https://www.southwest.com/",
            },
            {
                "name": "United Airlines",
                "official": "https://www.united.com/",
            },
            {
                "name": "JetBlue",
                "official": "https://www.jetblue.com/",
            },
        ],
    }
