# main.py — ¿QUÉ QUIERES LLEVAR? | May Roga LLC
from __future__ import annotations
import os,re
from pathlib import Path
from typing import Any,Optional
import httpx
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field

APP_VERSION="10.0.0"
BASE_DIR=Path(__file__).resolve().parent
STATIC_DIR=BASE_DIR/"static"
INDEX_FILE=STATIC_DIR/"index.html"

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","").strip()
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash").strip()

app=FastAPI(title="¿QUÉ QUIERES LLEVAR? | May Roga LLC",version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

if STATIC_DIR.exists():
    app.mount("/static",StaticFiles(directory=str(STATIC_DIR)),name="static")

class ItemCheckRequest(BaseModel):
    item_name:str=Field(...,min_length=1,max_length=300)
    destination:str="Cuba"
    luggage_type:str="mano"

class TripAnalysisRequest(BaseModel):
    origin:str=""
    destination:str=""
    date:str=""
    passengers:str="1"
    has_stops:str="direct"
    stop_location:str=""

class GeminiRequest(BaseModel):
    prompt:str=Field(...,min_length=1,max_length=10000)

AIRLINES=[
    {"name":"American Airlines","type":"Aerolínea comercial","url":"https://www.aa.com/"},
    {"name":"Delta Air Lines","type":"Aerolínea comercial","url":"https://www.delta.com/"},
    {"name":"United Airlines","type":"Aerolínea comercial","url":"https://www.united.com/"},
    {"name":"Southwest Airlines","type":"Aerolínea comercial","url":"https://www.southwest.com/"},
    {"name":"JetBlue","type":"Aerolínea comercial","url":"https://www.jetblue.com/"},
    {"name":"Havana Air","type":"Charter","url":"https://www.havanaair.com/"},
    {"name":"Aerocuba","type":"Charter","url":"https://www.aerocuba.com/"},
    {"name":"Anex / Xael Charters","type":"Charter","url":"https://www.anextours.com/"},
    {"name":"Invictus Charter","type":"Charter","url":"https://www.invictustours.com/"}
]

OFFICIAL_SOURCES={
    "aduana":{
        "name":"Aduana General de la República de Cuba",
        "url":"https://www.aduana.gob.cu/"
    },
    "dviajeros":{
        "name":"D’Viajeros",
        "url":"https://dviajeros.mitrans.gob.cu/"
    },
    "evisa":{
        "name":"eVisa Cuba",
        "url":"https://evisacuba.cu/"
    },
    "flights":{
        "name":"Google Flights",
        "url":"https://www.google.com/travel/flights"
    }
}

def clean_text(value:Any)->str:
    return re.sub(r"\s+"," ",str(value or "")).strip()

def local_item_check(item:str,destination:str,luggage_type:str)->dict:
    q=clean_text(item).lower()
    dest=clean_text(destination) or "Cuba"
    cuba="cuba" in dest.lower()

    if not q:
        return {
            "status":"REVISA ESTO ANTES DE VIAJAR",
            "recommendation":"Escribe el nombre del artículo para poder orientarte.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["arma","pistola","rifle","munición","municion","explosivo","granada"]):
        return {
            "status":"NO LO DES POR PERMITIDO",
            "recommendation":"Este tipo de artículo puede estar sujeto a prohibiciones o controles especiales. No lo lleves sin confirmar expresamente con la autoridad competente y la aerolínea.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["power bank","batería externa","bateria externa","litio","batería de litio","bateria de litio"]):
        return {
            "status":"REVISA LAS REGLAS DE BATERÍAS",
            "recommendation":"Las baterías y baterías externas tienen reglas específicas de transporte y capacidad. Su ubicación en el equipaje puede estar limitada. Confirma la capacidad y las condiciones de tu aerolínea antes de viajar.",
            "source":"Aduana de Cuba y aerolínea que opera tu vuelo"
        }

    if any(x in q for x in ["medicamento","medicina","pastilla","antibiótico","antibiotico","insulina","jeringa"]):
        return {
            "status":"PUEDES LLEVARLO SOLO TRAS REVISAR LAS CONDICIONES",
            "recommendation":"Los medicamentos pueden estar sujetos a reglas según el producto, cantidad, presentación y finalidad. Lleva la documentación que corresponda y confirma cualquier medicamento especial antes de viajar.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["perfume","colonia","shampoo","champú","crema","loción","locion","gel","líquido","liquido","cosmético","cosmetico"]):
        return {
            "status":"REVISA LAS REGLAS DE LÍQUIDOS",
            "recommendation":"Los líquidos, aerosoles, geles y cosméticos pueden tener límites diferentes según dónde viajen y los controles de seguridad. Confirma el envase, cantidad y tipo de equipaje antes de viajar.",
            "source":"Reglas de seguridad del aeropuerto y aerolínea"
        }

    if any(x in q for x in ["celular","teléfono","telefono","iphone","android","laptop","computadora","ordenador","tablet","ipad","cámara","camara","electrónico","electronico"]):
        return {
            "status":"GENERALMENTE ES UN ARTÍCULO TRANSPORTABLE",
            "recommendation":"Los equipos electrónicos pueden viajar, pero las baterías y determinadas condiciones de transporte tienen reglas específicas. Confirma las instrucciones de tu aerolínea y aeropuerto.",
            "source":"Aerolínea y autoridad de seguridad correspondiente"
        }

    if any(x in q for x in ["ropa","camisa","pantalón","pantalon","vestido","abrigo","zapatos","tenis","sandalias","ropa interior"]):
        return {
            "status":"REVISA CANTIDAD Y CONDICIONES",
            "recommendation":"La ropa y el calzado normalmente forman parte del equipaje del viajero, pero cantidad, peso, volumen y tratamiento aduanero pueden depender de las circunstancias del viaje.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["arroz","frijol","frijoles","café","cafe","galletas","conserva","conservas","comida","alimento","alimentos","chocolate","dulce","caramelo","pasta","harina","azúcar","azucar"]):
        return {
            "status":"REVISA EL ALIMENTO ANTES DE EMPACARLO",
            "recommendation":"Los alimentos pueden estar sujetos a restricciones según el producto, origen, presentación, cantidad y condiciones sanitarias o aduaneras. No asumas que todos los alimentos tienen la misma regla.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["carne","pollo","cerdo","res","pescado","marisco","embutido","queso","leche","huevo"]):
        return {
            "status":"REVISA ANTES DE VIAJAR",
            "recommendation":"Los productos de origen animal y algunos alimentos frescos o procesados pueden estar sujetos a controles sanitarios y restricciones especiales. Confirma el producto exacto antes de empacarlo.",
            "source":"Aduana y autoridades sanitarias correspondientes"
        }

    if any(x in q for x in ["herramienta","martillo","taladro","destornillador","sierra","cuchillo","navaja","alicate","llave"]):
        return {
            "status":"REVISA EL TIPO DE HERRAMIENTA Y EL EQUIPAJE",
            "recommendation":"Las herramientas pueden estar sujetas a restricciones de seguridad en cabina y a condiciones diferentes si viajan facturadas. Confirma el artículo exacto con la aerolínea.",
            "source":"Aerolínea y autoridad de seguridad del aeropuerto"
        }

    if any(x in q for x in ["repuesto","repuestos","pieza","piezas","automóvil","automovil","motor","alternador","bomba","filtro","repuesto de carro"]):
        return {
            "status":"REVISA LA PIEZA ESPECÍFICA",
            "recommendation":"Los repuestos pueden requerir una revisión especial por tamaño, peso, materiales, cantidades o características del artículo. No asumas que todas las piezas tienen la misma condición.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["electrodoméstico","electrodomestico","ventilador","microondas","licuadora","refrigerador","nevera","televisor","televisión","television","aire acondicionado","lavadora"]):
        return {
            "status":"REVISA PESO, CANTIDAD Y CONDICIONES ADUANERAS",
            "recommendation":"Los electrodomésticos y equipos grandes pueden estar sujetos a condiciones particulares por tipo, cantidad, valor, peso y equipaje. Confirma el artículo exacto antes de viajar.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["juguete","juguetes","muñeca","muneca","carriola","coche de bebé","coche de bebe","pañal","panal","biberón","biberon"]):
        return {
            "status":"REVISA EL ARTÍCULO Y LA CANTIDAD",
            "recommendation":"Los artículos infantiles pueden viajar, pero conviene confirmar las reglas del equipaje y, cuando corresponda, las condiciones aduaneras según cantidad y tipo.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["regalo","regalos","juguete","libro","libros","artículo del hogar","articulo del hogar","decoración","decoracion"]):
        return {
            "status":"REVISA CANTIDAD Y CARACTERÍSTICAS",
            "recommendation":"Muchos artículos personales o regalos pueden viajar, pero la cantidad, naturaleza, valor y características pueden cambiar su tratamiento. Confirma antes de viajar.",
            "source":"Aduana General de la República de Cuba"
        }

    if any(x in q for x in ["dinero","efectivo","cash","moneda","dólares","dolares"]):
        return {
            "status":"REVISA LAS REGLAS SOBRE DINERO",
            "recommendation":"El dinero y determinados instrumentos de pago pueden estar sujetos a reglas de declaración o límites. No asumas una cantidad sin verificar la normativa vigente.",
            "source":"Aduana General de la República de Cuba"
        }

    return {
        "status":"REVISA ESTO ANTES DE VIAJAR",
        "recommendation":f"No encontramos una regla local suficientemente específica para «{item}». Eso no significa que esté prohibido ni que esté automáticamente permitido. Confirma el artículo exacto, cantidad y forma de transporte en la fuente oficial.",
        "source":"Aduana General de la República de Cuba" if cuba else "Autoridad aduanera y aerolínea correspondientes"
    }

def parse_gemini_text(data:dict)->str:
    try:
        parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
        return "\n".join(str(p.get("text","")) for p in parts if p.get("text")).strip()
    except Exception:
        return ""

def normalize_ai_answer(text:str,item:str)->dict:
    text=clean_text(text)
    if not text:
        return local_item_check(item,"Cuba","mano")

    status="REVISA ESTO ANTES DE VIAJAR"

    upper=text.upper()

    if "PROHIBIDO" in upper or "NO SE PUEDE" in upper or "NO PUEDES" in upper:
        status="NO LO DES POR PERMITIDO"
    elif "PUEDES LLEVAR" in upper or "PERMITIDO" in upper:
        status="PUEDE SER POSIBLE, PERO DEBES CONFIRMAR"
    elif "REVIS" in upper:
        status="REVISA ESTO ANTES DE VIAJAR"

    return {
        "status":status,
        "recommendation":text,
        "source":"Confirma siempre en la fuente oficial correspondiente antes de viajar."
    }

async def ask_gemini(item:str,destination:str,luggage_type:str)->Optional[dict]:
    if not GEMINI_API_KEY:
        return None

    prompt=f"""
Eres un asistente de preparación de viajes de May Roga LLC.
No eres autoridad aduanera, aerolínea, gobierno ni asesor legal.
El usuario quiere saber qué debe revisar antes de transportar este artículo.

Artículo: {item}
Destino: {destination}
Tipo de equipaje indicado: {luggage_type}

Responde en español sencillo y humano.
No inventes cantidades, tarifas, permisos, límites, precios, impuestos,
rutas ni requisitos.
No afirmes que algo está permitido o prohibido si no puedes establecerlo
con seguridad.
Si depende de la aerolínea, equipaje, cantidad, valor, origen, presentación
o regulación vigente, dilo claramente.
Para Cuba, recuerda que las reglas aduaneras y sanitarias deben confirmarse
directamente con la autoridad oficial.
No solicites contraseñas, tarjetas, CVV, datos bancarios ni documentos
innecesarios.

Devuelve únicamente un párrafo breve de orientación práctica.
"""

    url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

    payload={
        "system_instruction":{
            "parts":[
                {
                    "text":"Proporciona orientación prudente para preparación de viajes. Nunca inventes reglas oficiales."
                }
            ]
        },
        "contents":[
            {
                "role":"user",
                "parts":[{"text":prompt}]
            }
        ],
        "generationConfig":{
            "temperature":0.2,
            "maxOutputTokens":500
        }
    }

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response=await client.post(
                url,
                params={"key":GEMINI_API_KEY},
                json=payload
            )

        if response.status_code!=200:
            return None

        data=response.json()
        text=parse_gemini_text(data)

        if not text:
            return None

        return normalize_ai_answer(text,item)

    except Exception:
        return None

@app.get("/",response_class=HTMLResponse)
async def root():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE),media_type="text/html")
    return HTMLResponse(
        "<h1>¿QUÉ QUIERES LLEVAR?</h1><p>No se encontró static/index.html.</p>",
        status_code=200
    )

@app.get("/api/health")
async def health():
    return {
        "status":"ok",
        "app":"¿QUÉ QUIERES LLEVAR?",
        "version":APP_VERSION,
        "gemini_configured":bool(GEMINI_API_KEY),
        "gemini_model":GEMINI_MODEL,
        "static_exists":STATIC_DIR.exists(),
        "index_exists":INDEX_FILE.exists()
    }

@app.post("/api/check-item")
async def check_item(request:ItemCheckRequest):
    item=clean_text(request.item_name)

    if not item:
        raise HTTPException(status_code=400,detail="Debes indicar un artículo.")

    local=local_item_check(
        item,
        request.destination,
        request.luggage_type
    )

    ai_result=await ask_gemini(
        item,
        clean_text(request.destination) or "Cuba",
        clean_text(request.luggage_type) or "mano"
    )

    if ai_result:
        result=ai_result
        result["source"]=(
            "Confirma directamente con la fuente oficial. "
            "Para Cuba: Aduana General de la República."
        )
    else:
        result=local

    result["item"]=item
    result["destination"]=clean_text(request.destination) or "Cuba"
    result["official_sources"]=[
        OFFICIAL_SOURCES["aduana"],
        OFFICIAL_SOURCES["dviajeros"],
        OFFICIAL_SOURCES["evisa"]
    ]

    return result

@app.get("/api/airlines")
async def airlines():
    return {
        "destination":"Cuba",
        "notice":"Consulta cada sitio oficial para confirmar rutas, fechas, horarios y disponibilidad.",
        "google_flights":OFFICIAL_SOURCES["flights"],
        "airlines":AIRLINES
    }

@app.get("/api/dviajeros")
async def dviajeros():
    return {
        "name":"D’Viajeros",
        "url":OFFICIAL_SOURCES["dviajeros"]["url"],
        "official":True,
        "notice":"La información y el formulario oficial deben completarse directamente en el sitio correspondiente."
    }

@app.get("/api/evisa")
async def evisa():
    return {
        "name":"eVisa Cuba",
        "url":OFFICIAL_SOURCES["evisa"]["url"],
        "official":True,
        "notice":"Consulta directamente el sitio oficial para conocer el proceso vigente."
    }

@app.get("/api/trip")
async def trip_info():
    return {
        "message":"La preparación del viaje se realiza en el navegador.",
        "storage":"No se almacenan datos personales del viaje en el servidor mediante este endpoint."
    }

@app.post("/api/analyze-trip")
async def analyze_trip(request:TripAnalysisRequest):
    origin=clean_text(request.origin)
    destination=clean_text(request.destination)
    stops=clean_text(request.has_stops)

    if not origin or not destination:
        raise HTTPException(status_code=400,detail="Faltan origen o destino.")

    if stops=="stops":
        explanation=(
            f"Tu práctica es un viaje de {origin} a {destination} con conexión. "
            "Confirma qué aerolínea opera cada tramo y pregunta cómo se manejará "
            "el equipaje durante la conexión."
        )
    else:
        explanation=(
            f"Tu práctica es un viaje de {origin} a {destination} sin conexión. "
            "Confirma directamente con la aerolínea las condiciones del boleto y equipaje."
        )

    return {
        "origin":origin,
        "destination":destination,
        "explanation":explanation
    }

@app.post("/api/gemini")
async def gemini_proxy(request:GeminiRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503,detail="Gemini no está configurado en Render.")

    url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

    payload={
        "contents":[
            {
                "role":"user",
                "parts":[{"text":request.prompt}]
            }
        ],
        "generationConfig":{
            "temperature":0.2,
            "maxOutputTokens":700
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response=await client.post(
                url,
                params={"key":GEMINI_API_KEY},
                json=payload
            )

        if response.status_code!=200:
            raise HTTPException(
                status_code=502,
                detail="El servicio de IA no respondió correctamente."
            )

        data=response.json()
        text=parse_gemini_text(data)

        return {
            "ok":True,
            "text":text
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="No fue posible consultar el servicio de IA."
        )

@app.get("/api/config")
async def config():
    return {
        "app_version":APP_VERSION,
        "gemini_configured":bool(GEMINI_API_KEY),
        "gemini_model":GEMINI_MODEL,
        "client_configuration":False
    }

@app.get("/api")
async def api_root():
    return {
        "app":"¿QUÉ QUIERES LLEVAR?",
        "version":APP_VERSION,
        "endpoints":[
            "/api/health",
            "/api/check-item",
            "/api/airlines",
            "/api/dviajeros",
            "/api/evisa",
            "/api/analyze-trip",
            "/api/trip"
        ]
    }

@app.get("/favicon.ico")
async def favicon():
    return HTMLResponse("",status_code=204)
