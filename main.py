import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles


# ============================================================
# ¿QUÉ QUIERES LLEVAR? | MAY ROGA LLC
# BACKEND PRINCIPAL
# ============================================================

VERSION = "3.0.0"

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
    description=(
        "Acompañamiento independiente para preparar un viaje, "
        "comprender vuelos, equipaje y procesos oficiales."
    ),
    version=VERSION,
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
# ARCHIVOS DEL FRONTEND
# ============================================================

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
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
    date: Optional[str] = ""
    passengers: Optional[str] = "1"
    has_stops: Optional[str] = "direct"
    stop_location: Optional[str] = ""


class GeminiRequest(BaseModel):
    prompt: str
    destination: Optional[str] = "Cuba"


# ============================================================
# UTILIDADES
# ============================================================

def normalize(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
    )


def item_result(
    status: str,
    recommendation: str,
    source: str,
    ai_used: bool = False,
):
    return {
        "status": status,
        "recommendation": recommendation,
        "source": source,
        "ai_used": ai_used,
    }


# ============================================================
# REGLAS LOCALES DE RESPALDO
# ============================================================

def local_item_check(
    item_name: str,
    destination: str = "Cuba",
    luggage_type: str = "mano",
):
    item = normalize(item_name)

    if not item:
        return item_result(
            "NECESITAMOS SABER QUÉ QUIERES LLEVAR",
            "Escribe el nombre del artículo para poder orientarte.",
            "Orientación May Roga LLC",
        )

    if any(
        word in item
        for word in (
            "power bank",
            "bateria",
            "batería",
            "baterias",
            "baterías",
            "pila de litio",
            "banco de energia",
            "banco de energía",
        )
    ):
        return item_result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Las baterías de litio y los power banks tienen reglas "
                "específicas de seguridad aérea. Como orientación general, "
                "los power banks deben transportarse en el equipaje de mano. "
                "Revisa siempre las reglas actuales de la aerolínea y del "
                "aeropuerto antes de viajar."
            ),
            "Orientación general de seguridad aérea",
        )

    if any(
        word in item
        for word in (
            "perfume",
            "liquido",
            "líquido",
            "crema",
            "shampoo",
            "champu",
            "champú",
            "colonia",
        )
    ):
        return item_result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Los líquidos pueden estar sujetos a límites de cantidad "
                "y controles de seguridad cuando viajas con equipaje de mano. "
                "Revisa las reglas vigentes del aeropuerto y de la aerolínea "
                "antes de empacar."
            ),
            "Orientación general de seguridad aeroportuaria",
        )

    if any(
        word in item
        for word in (
            "medicamento",
            "medicina",
            "medicinas",
            "pastilla",
        )
    ):
        return item_result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Los medicamentos pueden tener reglas especiales de "
                "transporte y también pueden existir requisitos del país "
                "de destino. Mantén el medicamento identificado y revisa "
                "las reglas oficiales antes de viajar."
            ),
            "Orientación general de viaje",
        )

    if any(
        word in item
        for word in (
            "laptop",
            "computadora",
            "ordenador",
            "tablet",
            "ipad",
            "camara",
            "cámara",
        )
    ):
        return item_result(
            "PUEDES LLEVARLO, PERO...",
            (
                "Los dispositivos electrónicos pueden requerir atención "
                "durante el control de seguridad. Llévalos de forma accesible "
                "para poder presentarlos si el personal de seguridad lo solicita "
                "y revisa las instrucciones de tu aeropuerto y aerolínea."
            ),
            "Orientación general de seguridad aeroportuaria",
        )

    return item_result(
        "REVISA ESTO ANTES DE VIAJAR",
        (
            f"Para «{item_name}», revisa las reglas de seguridad del "
            "aeropuerto, las condiciones de equipaje de tu aerolínea y, "
            "cuando corresponda, las reglas oficiales de entrada de "
            f"{destination}. Si tienes dudas, confirma el artículo antes "
            "de empacarlo."
        ),
        "Orientación May Roga LLC",
    )


# ============================================================
# GEMINI
# ============================================================

async def gemini_request(prompt: str):
    if not GEMINI_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
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


def detect_item_status(text: str):
    upper = text.upper()

    if "NO PUEDES LLEVARLO" in upper:
        return "NO PUEDES LLEVARLO"

    if "PUEDES LLEVARLO, PERO" in upper:
        return "PUEDES LLEVARLO, PERO..."

    if "PUEDES LLEVARLO" in upper:
        return "PUEDES LLEVARLO"

    return "REVISA ESTO ANTES DE VIAJAR"


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)

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
            <p>No se encontró static/index.html.</p>
        </body>
        </html>
        """,
        status_code=500,
    )


# ============================================================
# CHECK ITEM
# ============================================================

@app.post("/api/check-item")
async def check_item(data: ItemCheckRequest):

    item = data.item_name.strip()
    destination = (data.destination or "Cuba").strip()
    luggage = (data.luggage_type or "mano").strip()

    if not item:
        return item_result(
            "NECESITAMOS SABER QUÉ QUIERES LLEVAR",
            "Escribe el nombre del artículo para poder orientarte.",
            "Orientación May Roga LLC",
        )

    prompt = f"""
Eres el asistente de preparación de viajes de May Roga LLC.

La persona está preparando un viaje a:
{destination}

Artículo:
{item}

Tipo de equipaje:
{luggage}

Responde en español, de manera sencilla, humana y breve.

Tu función NO es sustituir a una aerolínea, aeropuerto,
autoridad gubernamental, aduana ni organismo oficial.

NO inventes requisitos.
NO inventes límites.
NO presentes información de IA como una regla oficial.
NO digas que algo está permitido o prohibido si no puedes
sostenerlo con una fuente oficial.

Diferencia claramente entre:
1. seguridad aeroportuaria,
2. reglas de equipaje de la aerolínea,
3. reglas de entrada del país.

Utiliza uno de estos estados solamente cuando corresponda:

PUEDES LLEVARLO
PUEDES LLEVARLO, PERO...
NO PUEDES LLEVARLO
REVISA ESTO ANTES DE VIAJAR

Después explica qué debe revisar o hacer la persona.

No solicites contraseñas, datos bancarios, CVV,
códigos de seguridad ni credenciales.
"""

    ai_text = await gemini_request(prompt)

    if ai_text:
        return item_result(
            detect_item_status(ai_text),
            ai_text,
            (
                "Orientación asistida por IA. "
                "Verifica siempre las fuentes oficiales."
            ),
            True,
        )

    result = local_item_check(
        item_name=item,
        destination=destination,
        luggage_type=luggage,
    )

    result["ai_used"] = False

    return result


# ============================================================
# ANALIZAR VIAJE
# ============================================================

@app.post("/api/analyze-trip")
async def analyze_trip(data: TripAnalysisRequest):

    origin = data.origin.strip()
    destination = data.destination.strip()
    flight_type = data.flight_type.strip()
    airline = (data.airline or "General").strip()

    if not origin or not destination:
        return JSONResponse(
            status_code=400,
            content={
                "status": "FALTA INFORMACIÓN",
                "message": (
                    "Necesitamos el origen y el destino "
                    "para continuar."
                ),
            },
        )

    if data.has_stops == "stops":
        flight_message = (
            "Tu viaje tiene una o más escalas. "
            "Además del destino final, revisa las condiciones "
            "de las conexiones y de los aeropuertos correspondientes."
        )
    else:
        flight_message = (
            "Tu viaje está marcado como directo. "
            "Aun así, debes revisar equipaje, documentos y "
            "condiciones directamente con la aerolínea."
        )

    return {
        "status": "OK",
        "origin": origin,
        "destination": destination,
        "date": data.date or "",
        "passengers": data.passengers or "1",
        "flight_type": flight_type,
        "airline": airline,
        "has_stops": data.has_stops or "direct",
        "stop_location": data.stop_location or "",
        "message": flight_message,
        "next_step": (
            "Continúa con la preparación del equipaje y revisa "
            "la información oficial antes de viajar."
        ),
    }


# ============================================================
# GEMINI PROXY
# ============================================================

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

    system_prompt = f"""
Eres un asistente de preparación de viajes de May Roga LLC.

Destino relacionado:
{data.destination or "Cuba"}

La aplicación solamente orienta y enseña.
No es una aerolínea, agencia de viajes, gobierno,
consulado, aeropuerto ni autoridad migratoria.

No inventes reglas ni requisitos.
No afirmes verificaciones que no hayas realizado.
Cuando una respuesta dependa de una fuente oficial,
indica que debe comprobarse directamente.

Consulta del usuario:
{prompt}
"""

    result = await gemini_request(system_prompt)

    if not result:
        return {
            "status": "UNAVAILABLE",
            "message": (
                "La orientación automática no está disponible "
                "en este momento."
            ),
        }

    return {
        "status": "OK",
        "text": result,
        "source": (
            "Orientación asistida por IA. "
            "Verifica la información en la fuente oficial correspondiente."
        ),
    }


# ============================================================
# CONFIGURACIÓN GEMINI
# ============================================================

@app.get("/api/config")
async def api_config():
    return {
        "gemini_available": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL if GEMINI_API_KEY else None,
    }


# ============================================================
# INFORMACIÓN DEL VIAJE
# ============================================================

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


# ============================================================
# SIMULADOR D'VIAJEROS
# ============================================================

@app.get("/api/dviajeros")
async def dviajeros_info():

    return {
        "status": "OK",
        "title": "Simulación D’Viajeros",
        "official_site": (
            "https://dviajeros.mitrans.gob.cu/"
        ),
        "message": (
            "Esta sección es una práctica educativa. "
            "No sustituye el formulario oficial."
        ),
    }


# ============================================================
# eVISA
# ============================================================

@app.get("/api/evisa")
async def evisa_info():

    return {
        "status": "OK",
        "title": "eVisa Cuba",
        "official_site": "https://evisacuba.cu/",
        "message": (
            "Consulta siempre el portal oficial para conocer "
            "el proceso vigente."
        ),
    }


# ============================================================
# AEROLÍNEAS
# ============================================================

@app.get("/api/airlines")
async def airlines():

    return {
        "status": "OK",
        "message": (
            "La información de una aerolínea debe confirmarse "
            "directamente con la aerolínea correspondiente."
        ),
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


# ============================================================
# SALUD DEL SERVICIO
# ============================================================

@app.get("/api/health")
async def health():

    return {
        "status": "healthy",
        "service": "Qu-Quieres-Llevar",
        "company": "May Roga LLC",
        "version": VERSION,
        "gemini_configured": bool(GEMINI_API_KEY),
        "static_index": INDEX_FILE.exists(),
    }


# ============================================================
# INFORMACIÓN DE LA APP
# ============================================================

@app.get("/api")
async def api_info():

    return {
        "name": "¿QUÉ QUIERES LLEVAR?",
        "company": "May Roga LLC",
        "version": VERSION,
        "status": "online",
        "endpoints": {
            "item_check": "/api/check-item",
            "trip_analysis": "/api/analyze-trip",
            "trip": "/api/trip",
            "gemini": "/api/gemini",
            "dviajeros": "/api/dviajeros",
            "evisa": "/api/evisa",
            "airlines": "/api/airlines",
            "config": "/api/config",
            "health": "/api/health",
        },
    }
