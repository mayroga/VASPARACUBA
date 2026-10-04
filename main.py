# main.py — ¿QUÉ QUIERES LLEVAR? | May Roga LLC | v12.0.0
from __future__ import annotations
import os,json,re,html
from typing import Any,Dict,List,Optional
from pathlib import Path
import httpx
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field

APP_VERSION="12.0.0"
APP_NAME="¿QUÉ QUIERES LLEVAR?"
COMPANY="May Roga LLC"
BASE_DIR=Path(__file__).resolve().parent
STATIC_DIR=BASE_DIR/"static"
INDEX_FILE=STATIC_DIR/"index.html"

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","").strip()
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash").strip()
GEMINI_URL=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

OFFICIAL_SOURCES={
    "aduana_cuba":{
        "name":"Aduana General de la República de Cuba",
        "url":"https://www.aduana.gob.cu/"
    },
    "dviajeros":{
        "name":"D'Viajeros",
        "url":"https://dviajeros.mitrans.gob.cu/"
    },
    "evisa":{
        "name":"eVisa Cuba",
        "url":"https://evisacuba.cu/"
    },
    "aa":{
        "name":"American Airlines",
        "url":"https://www.aa.com/"
    },
    "delta":{
        "name":"Delta Air Lines",
        "url":"https://www.delta.com/"
    },
    "united":{
        "name":"United Airlines",
        "url":"https://www.united.com/"
    },
    "southwest":{
        "name":"Southwest Airlines",
        "url":"https://www.southwest.com/"
    },
    "jetblue":{
        "name":"JetBlue",
        "url":"https://www.jetblue.com/"
    },
    "havana_air":{
        "name":"Havana Air",
        "url":"https://www.havanaair.com/"
    },
    "aerocuba":{
        "name":"Aerocuba",
        "url":"https://www.aerocuba.com/"
    },
    "anex":{
        "name":"Anex / Xael Charters",
        "url":"https://www.anextours.com/"
    },
    "invictus":{
        "name":"Invictus Charter",
        "url":"https://www.invictustours.com/"
    },
    "google_flights":{
        "name":"Google Flights",
        "url":"https://www.google.com/travel/flights"
    }
}

AIRLINES=[
    {"id":"aa","name":"American Airlines","type":"Aerolínea","url":"https://www.aa.com/"},
    {"id":"delta","name":"Delta Air Lines","type":"Aerolínea","url":"https://www.delta.com/"},
    {"id":"united","name":"United Airlines","type":"Aerolínea","url":"https://www.united.com/"},
    {"id":"southwest","name":"Southwest Airlines","type":"Aerolínea","url":"https://www.southwest.com/"},
    {"id":"jetblue","name":"JetBlue","type":"Aerolínea","url":"https://www.jetblue.com/"},
    {"id":"havana_air","name":"Havana Air","type":"Charter","url":"https://www.havanaair.com/"},
    {"id":"aerocuba","name":"Aerocuba","type":"Charter","url":"https://www.aerocuba.com/"},
    {"id":"anex","name":"Anex / Xael Charters","type":"Charter","url":"https://www.anextours.com/"},
    {"id":"invictus","name":"Invictus Charter","type":"Charter","url":"https://www.invictustours.com/"},
    {"id":"google_flights","name":"Google Flights","type":"Buscador","url":"https://www.google.com/travel/flights"}
]

app=FastAPI(title=APP_NAME,version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
if STATIC_DIR.exists():
    app.mount("/static",StaticFiles(directory=str(STATIC_DIR)),name="static")

class ItemCheckRequest(BaseModel):
    item_name:str=Field(...,min_length=1,max_length=500)
    destination:str="Cuba"
    luggage_type:str="Todavía no sé"
    origin:str=""
    airline:str=""
    context:str=""

class TripRequest(BaseModel):
    origin:str=""
    destination:str="Cuba"
    passengers:int=1
    stops:int=0
    luggage:str=""
    airline:str=""

class GeminiRequest(BaseModel):
    prompt:str=Field(...,min_length=1,max_length=12000)

def clean_text(value:Any,max_len:int=1000)->str:
    if value is None:
        return ""
    value=str(value).strip()
    value=re.sub(r"\s+"," ",value)
    return value[:max_len]

def normalize_url(url:Any)->str:
    value=clean_text(url,500)
    if value.startswith("https://") or value.startswith("http://"):
        return value
    return ""

def source_for_destination(destination:str)->List[Dict[str,str]]:
    d=clean_text(destination,100).lower()
    if "cuba" in d:
        return [
            OFFICIAL_SOURCES["aduana_cuba"],
            OFFICIAL_SOURCES["dviajeros"],
            OFFICIAL_SOURCES["evisa"]
        ]
    return []

def official_sources_for_item(destination:str,airline:str="")->List[Dict[str,str]]:
    result=source_for_destination(destination)
    a=clean_text(airline,100).lower()
    airline_map={
        "american":OFFICIAL_SOURCES["aa"],
        "american airlines":OFFICIAL_SOURCES["aa"],
        "delta":OFFICIAL_SOURCES["delta"],
        "delta air lines":OFFICIAL_SOURCES["delta"],
        "united":OFFICIAL_SOURCES["united"],
        "southwest":OFFICIAL_SOURCES["southwest"],
        "jetblue":OFFICIAL_SOURCES["jetblue"],
        "havana air":OFFICIAL_SOURCES["havana_air"],
        "aerocuba":OFFICIAL_SOURCES["aerocuba"],
        "anex":OFFICIAL_SOURCES["anex"],
        "xael":OFFICIAL_SOURCES["anex"],
        "invictus":OFFICIAL_SOURCES["invictus"]
    }
    for key,value in airline_map.items():
        if key in a and value not in result:
            result.append(value)
            break
    return result

def local_item_check(item:str,destination:str,luggage_type:str,airline:str="")->Dict[str,Any]:
    x=clean_text(item,500).lower()
    cuba="cuba" in clean_text(destination,100).lower()
    sources=official_sources_for_item(destination,airline)

    status="REVISA"
    recommendation="Necesitamos comprobar las características de este artículo antes de darte una respuesta responsable."
    article="Este artículo puede estar sujeto a reglas diferentes según sus características y según cómo se transporte."
    what_matters=[]
    questions=[]
    where_to_look=[]
    warnings=[]

    if any(k in x for k in [
        "arma","pistola","rifle","munición","municion","explosivo",
        "granada","fuego artificial","firework","taser"
    ]):
        status="NO LO DES POR PERMITIDO"
        recommendation="No debes asumir que este artículo puede viajar en avión. Requiere una comprobación específica de las normas de seguridad aérea, de la aerolínea y, cuando corresponda, de las autoridades del destino."
        article="Los artículos de esta categoría pueden estar sujetos a restricciones especiales y no deben tratarse como equipaje común."
        what_matters=["tipo exacto del artículo","si contiene munición o material peligroso","forma de transporte"]
        questions=["¿Qué artículo exacto es?","¿Contiene munición, combustible o material peligroso?"]
        where_to_look=["Reglas de artículos restringidos o prohibidos de la aerolínea","Información oficial de seguridad aérea","Reglas de entrada del país de destino"]
        warnings=["No lo lleves al aeropuerto suponiendo que está permitido."]

    elif any(k in x for k in [
        "power bank","bateria externa","batería externa","bateria",
        "batería","power station","estacion de energia","estación de energía",
        "generador portatil","generador portátil","litio","lithium"
    ]):
        status="REVISA"
        recommendation="Puede ser transportable en determinadas condiciones, pero no es responsable decirte simplemente 'sí'. Las características de la batería y la forma de transporte pueden cambiar la respuesta."
        article="Las baterías de litio y los equipos que las contienen tienen reglas específicas para el transporte aéreo."
        what_matters=[
            "capacidad de la batería, normalmente expresada en Wh",
            "tipo de batería",
            "si la batería está instalada o es independiente",
            "si se transporta en cabina o equipaje facturado",
            "características del equipo completo"
        ]
        questions=[
            "¿Cuántos Wh indica la batería o el equipo?",
            "¿La batería está instalada o es una batería independiente?",
            "¿Quieres llevarla en cabina o en equipaje facturado?"
        ]
        where_to_look=[
            "Reglas de equipaje y baterías de litio de la aerolínea",
            "Información oficial de seguridad aérea",
            "Si viajas a Cuba, reglas de Aduana para la entrada del artículo"
        ]
        warnings=["No escondas ni declares de forma incorrecta una batería o equipo con batería."]

    elif any(k in x for k in [
        "carro","auto","automovil","automóvil","coche","vehiculo","vehículo",
        "motorcycle","motocicleta","moto","scooter","patineta","bicicleta",
        "e-bike","bicicleta electrica","bicicleta eléctrica","motor","motor de carro",
        "pieza de carro","repuesto","autoparte","auto parte"
    ]):
        status="REVISA"
        recommendation="Este artículo no debe tratarse como equipaje normal sin comprobar primero sus características. El tamaño, peso, batería, combustible, piezas y finalidad pueden cambiar completamente las condiciones de transporte y de entrada al destino."
        article="Vehículos, motores, bicicletas eléctricas, scooters y determinadas piezas pueden estar sujetos a reglas diferentes de transporte aéreo y de importación."
        what_matters=[
            "qué artículo exacto es",
            "peso y dimensiones",
            "si contiene batería",
            "tipo y capacidad de la batería, si corresponde",
            "si contiene combustible, aceite u otra sustancia",
            "si se trata de una pieza independiente"
        ]
        questions=[
            "¿Qué artículo exacto quieres transportar?",
            "¿Cuánto pesa y cuáles son sus dimensiones?",
            "¿Tiene batería? Si la tiene, ¿qué capacidad indica?",
            "¿Contiene combustible, aceite u otro líquido?"
        ]
        where_to_look=[
            "Reglas de equipaje especial o carga de la aerolínea",
            "Reglas de artículos peligrosos o restringidos de la aerolínea",
            "Si el destino es Cuba, Aduana General de la República de Cuba"
        ]

    elif any(k in x for k in [
        "medicina","medicamento","medicamentos","medicine","vitamina",
        "vitaminas","pastilla","pastillas","droga","prescripcion","prescripción"
    ]):
        status="REVISA"
        recommendation="No es correcto clasificar todos los medicamentos de la misma manera. El tipo de producto, la cantidad, la presentación y las reglas del país de destino pueden ser importantes."
        article="Los medicamentos y productos relacionados pueden estar sujetos tanto a reglas de transporte como a reglas de entrada al país."
        what_matters=["nombre exacto del producto","presentación","cantidad","si requiere receta","reglas del destino"]
        questions=["¿Cuál es el nombre exacto del medicamento o producto?","¿Cuántas unidades llevas?","¿Es un medicamento con receta?"]
        where_to_look=["Reglas de equipaje de la aerolínea","Requisitos oficiales del país de destino"]
        if cuba:
            where_to_look.append("Aduana General de la República de Cuba")

    elif any(k in x for k in [
        "perfume","shampoo","champu","champú","crema","locion","loción",
        "gel","liquido","líquido","cosmetico","cosmético","spray","aerosol"
    ]):
        status="REVISA"
        recommendation="Este tipo de producto puede estar sujeto a reglas de transporte, especialmente por tratarse de un líquido, aerosol o producto similar. La cantidad y el lugar donde se transporta pueden ser importantes."
        article="Las reglas de seguridad del transporte aéreo pueden tratar de manera distinta los líquidos, aerosoles y otros productos."
        what_matters=["cantidad o volumen","tipo exacto del producto","si es aerosol","si va en cabina o facturado"]
        questions=["¿Cuánto contiene el envase?","¿Es líquido, gel, aerosol o crema?","¿Lo llevarás en cabina o facturado?"]
        where_to_look=["Reglas de equipaje de mano de la aerolínea","Reglas oficiales de seguridad aérea"]

    elif any(k in x for k in [
        "comida","comida preparada","arroz","frijoles","habichuela","cafe","café",
        "carne","queso","leche","embutido","pollo","pescado","alimento","alimentos",
        "food","semilla","semillas","fruta","verdura"
    ]):
        status="REVISA"
        recommendation="Que un alimento pueda subir al avión no significa automáticamente que pueda entrar al país. Hay que separar las reglas de transporte de las reglas de importación y de Aduana."
        article="Los alimentos pueden tener condiciones distintas para el transporte aéreo y para su entrada al país de destino."
        what_matters=["tipo exacto de alimento","si está preparado o industrialmente empacado","cantidad","si contiene productos animales o vegetales","reglas del destino"]
        questions=["¿Qué alimento exacto es?","¿Está sellado de fábrica o preparado en casa?","¿Contiene carne, lácteos, semillas o productos vegetales?"]
        where_to_look=["Reglas de equipaje de la aerolínea","Reglas oficiales de entrada de alimentos del país de destino"]
        if cuba:
            where_to_look.append("Aduana General de la República de Cuba")

    elif any(k in x for k in [
        "televisor","television","televisión","tv","computadora","ordenador",
        "laptop","tablet","celular","telefono","teléfono","camara","cámara",
        "electronico","electrónico","electrodomestico","electrodoméstico"
    ]):
        status="REVISA"
        recommendation="Este tipo de equipo normalmente necesita comprobarse por sus características de transporte y, si entra a otro país, por las reglas aplicables a su importación. No debe asumirse una cantidad o condición sin comprobarla."
        article="Los dispositivos electrónicos pueden estar sujetos a reglas de equipaje y, en algunos destinos, a reglas aduaneras."
        what_matters=["tipo de equipo","peso y dimensiones","si contiene batería de litio","cantidad de unidades","reglas del destino"]
        questions=["¿Qué equipo exacto es?","¿Tiene batería de litio?","¿Cuántas unidades llevas?"]
        where_to_look=["Reglas de equipaje de la aerolínea","Reglas oficiales de Aduana del destino"]
        if cuba:
            where_to_look.append("Aduana General de la República de Cuba")

    elif any(k in x for k in [
        "herramienta","herramientas","tool","taladro","cuchillo","navaja",
        "destornillador","martillo","sierra","drill"
    ]):
        status="REVISA"
        recommendation="Las herramientas no deben clasificarse solamente por su nombre. Algunas pueden tener restricciones en cabina aunque puedan transportarse de otra manera."
        article="La seguridad aérea puede establecer condiciones diferentes para herramientas y objetos que puedan causar lesiones."
        what_matters=["tipo exacto de herramienta","tamaño","si tiene filo o punta","si funciona con batería","cabina o equipaje facturado"]
        questions=["¿Qué herramienta exacta es?","¿Tiene filo, punta o batería?","¿Quieres llevarla en cabina o facturada?"]
        where_to_look=["Reglas de artículos restringidos de la aerolínea","Reglas oficiales de seguridad aérea"]

    elif any(k in x for k in [
        "ropa","ropa de vestir","camisa","pantalon","pantalón","zapatos",
        "zapato","vestido","abrigo","libro","juguete","regalo","peluche"
    ]):
        status="REVISA"
        recommendation="Este artículo no parece pertenecer por su descripción a una categoría especial de seguridad aérea, pero la respuesta final puede depender de su cantidad, características y de las reglas de entrada del destino."
        article="Los artículos personales pueden tener reglas distintas cuando se consideran equipaje personal o mercancía."
        what_matters=["cantidad","tipo exacto","si es para uso personal o comercial","reglas de entrada del destino"]
        questions=["¿Cuántas unidades llevas?","¿Son para uso personal o para otra finalidad?"]
        where_to_look=["Reglas de equipaje de la aerolínea"]
        if cuba:
            where_to_look.append("Aduana General de la República de Cuba")

    else:
        status="REVISA"
        recommendation="Puedo ayudarte a determinar qué debes comprobar, pero no sería correcto afirmar que el artículo está permitido o prohibido sin conocer sus características y las reglas oficiales aplicables."
        article="El nombre de un producto por sí solo no siempre permite determinar sus condiciones de transporte o de entrada al destino."
        what_matters=[
            "tipo exacto del artículo",
            "cantidad",
            "peso y dimensiones cuando sean relevantes",
            "si contiene batería, líquido, gas, combustible u otra sustancia",
            "si se transporta en cabina o facturado",
            "reglas del país de destino"
        ]
        questions=[
            "¿Cuál es el modelo o tipo exacto?",
            "¿Tiene batería, líquido, gas, combustible o alguna sustancia especial?",
            "¿Cuántas unidades llevas?",
            "¿Quieres llevarlo en cabina o en equipaje facturado?"
        ]
        where_to_look=["Reglas de equipaje y artículos restringidos de la aerolínea"]
        if cuba:
            where_to_look.append("Aduana General de la República de Cuba")

    if luggage_type and luggage_type.lower() not in ["todavía no sé","no sé",""]:
        what_matters.append(f"forma de transporte indicada: {clean_text(luggage_type,100)}")

    return {
        "status":status,
        "article":article,
        "recommendation":recommendation,
        "what_matters":what_matters,
        "questions_to_confirm":questions,
        "where_to_look":where_to_look,
        "warnings":warnings,
        "official_sources":sources,
        "source":sources[0]["url"] if sources else "",
        "source_name":sources[0]["name"] if sources else "",
        "ai_available":False
    }

def extract_json(text:str)->Optional[Dict[str,Any]]:
    if not text:
        return None
    value=text.strip()
    value=re.sub(r"^```(?:json)?\s*","",value,flags=re.I)
    value=re.sub(r"\s*```$","",value)
    try:
        obj=json.loads(value)
        if isinstance(obj,dict):
            return obj
    except Exception:
        pass
    start=value.find("{")
    end=value.rfind("}")
    if start>=0 and end>start:
        try:
            obj=json.loads(value[start:end+1])
            if isinstance(obj,dict):
                return obj
        except Exception:
            return None
    return None

def allowed_source(url:str,destination:str,airline:str)->bool:
    u=normalize_url(url)
    if not u:
        return False
    known={v["url"].rstrip("/") for v in OFFICIAL_SOURCES.values()}
    if u.rstrip("/") in known:
        return True
    d=clean_text(destination,100).lower()
    a=clean_text(airline,100).lower()
    if "cuba" in d:
        return any(host in u.lower() for host in [
            "aduana.gob.cu","mitrans.gob.cu","evisacuba.cu",
            "aa.com","delta.com","united.com","southwest.com",
            "jetblue.com","havanaair.com","aerocuba.com",
            "anextours.com","invictustours.com"
        ])
    if a:
        return any(host in u.lower() for host in [
            "aa.com","delta.com","united.com","southwest.com",
            "jetblue.com","havanaair.com","aerocuba.com",
            "anextours.com","invictustours.com"
        ])
    return False

def normalize_ai_answer(obj:Dict[str,Any],fallback:Dict[str,Any],destination:str,airline:str)->Dict[str,Any]:
    status=clean_text(obj.get("status") or fallback["status"],80).upper()
    valid_status={"PUEDES","REVISA","NO LO DES POR PERMITIDO","NO"}
    if status not in valid_status:
        status="REVISA"

    recommendation=clean_text(
        obj.get("recommendation") or obj.get("answer") or fallback["recommendation"],2500
    )
    article=clean_text(obj.get("article") or fallback["article"],1800)

    def clean_list(value,fallback_value,max_items=10,max_len=500):
        if not isinstance(value,list):
            return fallback_value
        result=[]
        for x in value[:max_items]:
            t=clean_text(x,max_len)
            if t:
                result.append(t)
        return result or fallback_value

    what_matters=clean_list(obj.get("what_matters"),fallback["what_matters"])
    questions=clean_list(obj.get("questions_to_confirm"),fallback["questions_to_confirm"])
    where=clean_list(obj.get("where_to_look"),fallback["where_to_look"])
    warnings=clean_list(obj.get("warnings"),fallback["warnings"])

    sources=[]
    raw_sources=obj.get("official_sources",[])
    if isinstance(raw_sources,list):
        for item in raw_sources[:8]:
            if isinstance(item,dict):
                url=normalize_url(item.get("url"))
                name=clean_text(item.get("name"),200)
                if url and allowed_source(url,destination,airline):
                    sources.append({"name":name or url,"url":url})
            elif isinstance(item,str):
                url=normalize_url(item)
                if url and allowed_source(url,destination,airline):
                    sources.append({"name":url,"url":url})

    if not sources:
        sources=fallback["official_sources"]

    return {
        "status":status,
        "article":article,
        "recommendation":recommendation,
        "what_matters":what_matters,
        "questions_to_confirm":questions,
        "where_to_look":where,
        "warnings":warnings,
        "official_sources":sources,
        "source":sources[0]["url"] if sources else "",
        "source_name":sources[0]["name"] if sources else "",
        "ai_available":True
    }

def build_gemini_prompt(req:ItemCheckRequest,fallback:Dict[str,Any])->str:
    item=clean_text(req.item_name,500)
    destination=clean_text(req.destination,100) or "Cuba"
    luggage=clean_text(req.luggage_type,100) or "Todavía no sé"
    origin=clean_text(req.origin,100)
    airline=clean_text(req.airline,150)
    context=clean_text(req.context,1000)

    sources=official_sources_for_item(destination,airline)
    source_text="\n".join(f"- {x['name']}: {x['url']}" for x in sources) or "- No hay una fuente oficial específica configurada para este destino."

    rules=[
        "Eres el motor profesional de orientación de una aplicación de May Roga LLC.",
        "Tu respuesta será mostrada directamente a una persona que quiere viajar y necesita saber qué debe hacer con un artículo o mercancía.",
        "NO menciones Gemini, inteligencia artificial, IA, modelo, sistema, prompt ni tecnología.",
        "Nunca digas que la respuesta fue generada por IA.",
        "No inventes leyes, prohibiciones, permisos, cantidades, pesos, dimensiones, límites de Wh, tarifas, impuestos, horarios, disponibilidad, rutas ni requisitos.",
        "No conviertas una suposición en un hecho.",
        "No afirmes que un artículo está permitido solamente porque parece común.",
        "No afirmes que un artículo está prohibido si no tienes una base oficial suficiente.",
        "Cuando no puedas confirmar algo, usa REVISA y explica exactamente qué debe comprobar la persona.",
        "La respuesta debe ayudar. Nunca respondas solamente 'consulta el sitio oficial'.",
        "Primero explica qué significa la situación para la persona.",
        "Después explica qué característica concreta puede cambiar la respuesta.",
        "Después indica qué debe comprobar y dónde.",
        "Distingue siempre entre seguridad del transporte aéreo, reglas de la aerolínea, equipaje y reglas de Aduana/importación.",
        "Que algo pueda subir al avión NO significa automáticamente que pueda entrar al país.",
        "Que algo pueda entrar al país NO significa automáticamente que pueda ir en cabina.",
        "Para baterías, power banks, estaciones de energía, vehículos eléctricos y equipos similares identifica la capacidad, tipo, instalación y forma de transporte como datos potencialmente importantes, pero no inventes límites.",
        "Para alimentos identifica si están industrialmente empacados, su composición y las reglas de entrada, sin inventar cantidades.",
        "Para medicamentos identifica el nombre, presentación, cantidad y si existe receta cuando sea relevante.",
        "Para vehículos, motores, bicicletas, scooters, piezas y herramientas identifica tamaño, peso, batería, combustible, líquidos y características especiales cuando correspondan.",
        "Haz solamente preguntas que realmente puedan cambiar la respuesta.",
        "Si faltan datos, no bloquees al usuario: explica lo que ya se puede saber y luego pide los datos faltantes.",
        "Si el destino es Cuba, separa claramente transporte aéreo de entrada por Aduana.",
        "Las fuentes deben ser oficiales. No uses blogs, foros, Reddit, TikTok, redes sociales ni páginas comerciales como autoridad.",
        "Si una fuente oficial no confirma un dato concreto, dilo claramente.",
        "No pidas contraseñas, CVV, códigos de seguridad, credenciales bancarias ni datos innecesarios.",
        "Devuelve únicamente JSON válido, sin markdown y sin texto fuera del JSON.",
        "El campo status solamente puede ser PUEDES, REVISA o NO LO DES POR PERMITIDO.",
        "PUEDES solo debe utilizarse cuando exista una base suficientemente clara para una orientación positiva.",
        "NO LO DES POR PERMITIDO debe utilizarse cuando exista una razón clara para no asumir que puede transportarse.",
        "REVISA es obligatorio cuando faltan datos materiales o la regla depende de confirmación.",
        "El campo recommendation debe ser profesional, sencillo, directo y útil; nunca debe dejar a la persona sin siguiente paso.",
        "El campo where_to_look debe decir qué sección, tema o regla debe buscar en la fuente oficial cuando sea razonablemente identificable.",
        "No inventes nombres de secciones si no estás seguro.",
        "No muestres ninguna etiqueta técnica al usuario."
    ]

    schema={
        "status":"PUEDES | REVISA | NO LO DES POR PERMITIDO",
        "article":"explicación breve de qué se está evaluando",
        "recommendation":"respuesta principal clara y accionable",
        "what_matters":["características que pueden cambiar la respuesta"],
        "questions_to_confirm":["preguntas realmente necesarias"],
        "where_to_look":["qué debe comprobar y dónde"],
        "warnings":["advertencias importantes"],
        "official_sources":[{"name":"fuente oficial","url":"URL oficial"}]
    }

    return "\n".join(rules)+(
        "\n\nDATOS DE LA CONSULTA:\n"
        f"Artículo: {item}\n"
        f"Destino: {destination}\n"
        f"Origen: {origin or 'No indicado'}\n"
        f"Equipaje: {luggage}\n"
        f"Aerolínea: {airline or 'No indicada'}\n"
        f"Contexto adicional: {context or 'Ninguno'}\n"
        "\nFUENTES OFICIALES DISPONIBLES:\n"+source_text+
        "\n\nORIENTACIÓN LOCAL DE RESPALDO. NO LA PRESENTES COMO LEY NI COMO CONFIRMACIÓN OFICIAL:\n"+
        json.dumps({
            "status":fallback["status"],
            "article":fallback["article"],
            "recommendation":fallback["recommendation"],
            "what_matters":fallback["what_matters"],
            "questions_to_confirm":fallback["questions_to_confirm"]
        },ensure_ascii=False)+
        "\n\nFORMATO JSON OBLIGATORIO:\n"+
        json.dumps(schema,ensure_ascii=False)
    )

async def call_gemini(req:ItemCheckRequest,fallback:Dict[str,Any])->Optional[Dict[str,Any]]:
    if not GEMINI_API_KEY:
        return None

    prompt=build_gemini_prompt(req,fallback)

    payload={
        "systemInstruction":{
            "parts":[
                {"text":"Responde únicamente con JSON válido. No menciones tecnología ni IA al usuario."}
            ]
        },
        "contents":[
            {
                "role":"user",
                "parts":[{"text":prompt}]
            }
        ],
        "generationConfig":{
            "temperature":0.1,
            "maxOutputTokens":1800
        }
    }

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response=await client.post(
                GEMINI_URL,
                params={"key":GEMINI_API_KEY},
                json=payload
            )
        if response.status_code>=400:
            return None

        data=response.json()
        candidates=data.get("candidates") or []
        if not candidates:
            return None

        parts=((candidates[0].get("content") or {}).get("parts") or [])
        text_parts=[]
        for part in parts:
            if isinstance(part,dict) and part.get("text"):
                text_parts.append(part["text"])

        result=extract_json("\n".join(text_parts))
        if not result:
            return None

        return result
    except Exception:
        return None

def public_item_response(req:ItemCheckRequest,fallback:Dict[str,Any],ai_obj:Optional[Dict[str,Any]])->Dict[str,Any]:
    if ai_obj:
        result=normalize_ai_answer(
            ai_obj,
            fallback,
            req.destination,
            req.airline
        )
    else:
        result=fallback.copy()
        result["ai_available"]=False

    # Nunca mostramos información técnica sobre el motor al usuario.
    result.pop("model",None)
    result.pop("provider",None)
    result.pop("technology",None)
    return result

@app.get("/")
async def root():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return JSONResponse({
        "app":APP_NAME,
        "company":COMPANY,
        "version":APP_VERSION,
        "message":"Aplicación activa. Falta static/index.html."
    })

@app.get("/favicon.ico")
async def favicon():
    icon=STATIC_DIR/"favicon.ico"
    if icon.exists():
        return FileResponse(str(icon))
    raise HTTPException(status_code=404,detail="favicon no disponible")

@app.get("/api")
async def api_info():
    return {
        "app":APP_NAME,
        "company":COMPANY,
        "version":APP_VERSION,
        "status":"ok",
        "gemini_configured":bool(GEMINI_API_KEY),
        "client_does_not_receive_api_key":True
    }

@app.get("/api/health")
async def health():
    return {
        "status":"ok",
        "app":APP_NAME,
        "version":APP_VERSION,
        "gemini_configured":bool(GEMINI_API_KEY)
    }

@app.get("/api/config")
async def config():
    # Nunca devuelve la clave.
    return {
        "app":APP_NAME,
        "company":COMPANY,
        "version":APP_VERSION,
        "gemini_configured":bool(GEMINI_API_KEY),
        "gemini_model":GEMINI_MODEL if GEMINI_API_KEY else "",
        "show_ai_brand":False
    }

@app.get("/api/airlines")
async def airlines():
    return {
        "status":"ok",
        "title":"Aerolíneas y charters para consultar vuelos hacia Cuba",
        "airlines":AIRLINES
    }

@app.get("/api/dviajeros")
async def dviajeros():
    return {
        "status":"ok",
        "name":"D'Viajeros",
        "url":OFFICIAL_SOURCES["dviajeros"]["url"],
        "official":True,
        "message":"Usa el sitio oficial para completar y revisar el formulario."
    }

@app.get("/api/evisa")
async def evisa():
    return {
        "status":"ok",
        "name":"eVisa Cuba",
        "url":OFFICIAL_SOURCES["evisa"]["url"],
        "official":True,
        "message":"Usa el sitio oficial para consultar y realizar el proceso correspondiente."
    }

@app.post("/api/check-item")
async def check_item(req:ItemCheckRequest):
    item=clean_text(req.item_name,500)
    if not item:
        raise HTTPException(status_code=400,detail="Escribe qué quieres llevar.")

    fallback=local_item_check(
        item,
        req.destination,
        req.luggage_type,
        req.airline
    )

    ai_obj=await call_gemini(req,fallback)
    return public_item_response(req,fallback,ai_obj)

@app.post("/api/trip")
async def trip(req:TripRequest):
    destination=clean_text(req.destination,100) or "Cuba"
    sources=source_for_destination(destination)
    return {
        "status":"ok",
        "origin":clean_text(req.origin,100),
        "destination":destination,
        "passengers":max(1,min(req.passengers,20)),
        "stops":max(0,min(req.stops,20)),
        "luggage":clean_text(req.luggage,200),
        "airline":clean_text(req.airline,150),
        "official_sources":sources
    }

@app.post("/api/analyze-trip")
async def analyze_trip(req:TripRequest):
    destination=clean_text(req.destination,100) or "Cuba"
    notes=[]

    if not clean_text(req.origin):
        notes.append("Falta indicar el lugar de salida.")
    if not clean_text(req.airline):
        notes.append("Todavía no has seleccionado una aerolínea.")
    if not clean_text(req.luggage):
        notes.append("Todavía no has definido cómo llevarás el equipaje.")

    if "cuba" in destination.lower():
        notes.append("Para Cuba deben revisarse por separado las reglas de vuelo/equipaje y las reglas de entrada por Aduana.")

    return {
        "status":"ok",
        "ready":len(notes)==0,
        "notes":notes,
        "next_action":(
            "Puedes continuar con la preparación."
            if not notes else
            "Completa primero los puntos indicados para obtener una orientación más útil."
        ),
        "official_sources":source_for_destination(destination)
    }

@app.post("/api/gemini")
async def gemini_endpoint(req:GeminiRequest):
    # Se conserva el endpoint para compatibilidad con versiones anteriores.
    # La aplicación no entrega la API key al navegador.
    if not GEMINI_API_KEY:
        return {
            "status":"unavailable",
            "message":"El servicio de consulta no está configurado en este momento."
        }

    prompt=(
        "Responde de forma profesional, sencilla y directa. "
        "No menciones Gemini ni inteligencia artificial. "
        "No inventes información. Si no puedes confirmar un dato, dilo y "
        "explica qué fuente oficial debe consultarse.\n\n"+
        clean_text(req.prompt,12000)
    )

    payload={
        "contents":[
            {"role":"user","parts":[{"text":prompt}]}
        ],
        "generationConfig":{
            "temperature":0.1,
            "maxOutputTokens":1800
        }
    }

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response=await client.post(
                GEMINI_URL,
                params={"key":GEMINI_API_KEY},
                json=payload
            )

        if response.status_code>=400:
            return {
                "status":"unavailable",
                "message":"No fue posible obtener la consulta en este momento."
            }

        data=response.json()
        candidates=data.get("candidates") or []
        if not candidates:
            return {
                "status":"unavailable",
                "message":"No se recibió una respuesta útil."
            }

        parts=((candidates[0].get("content") or {}).get("parts") or [])
        text_parts=[
            p.get("text","") for p in parts
            if isinstance(p,dict) and p.get("text")
        ]
        answer="\n".join(text_parts).strip()

        return {
            "status":"ok",
            "answer":answer
        }
    except Exception:
        return {
            "status":"unavailable",
            "message":"No fue posible completar la consulta en este momento."
        }

@app.get("/api/sources")
async def sources():
    return {
        "status":"ok",
        "sources":list(OFFICIAL_SOURCES.values())
    }

@app.get("/api/legal")
async def legal():
    return {
        "status":"ok",
        "company":COMPANY,
        "notice":(
            "¿QUÉ QUIERES LLEVAR? es una herramienta independiente de "
            "orientación y preparación. No es una aerolínea, agencia de viajes, "
            "autoridad aduanera, autoridad migratoria ni organismo gubernamental. "
            "Las reglas oficiales y las decisiones finales corresponden a las "
            "autoridades y al transportista aplicables."
        )
    }

@app.get("/api/guide")
async def guide():
    return {
        "status":"ok",
        "title":"Guía para preparar tu viaje",
        "steps":[
            {"id":1,"title":"Prepara tu vuelo","action":"Revisa opciones de vuelo y la aerolínea."},
            {"id":2,"title":"Entiende tu equipaje","action":"Comprueba qué tipo de equipaje tienes y las reglas aplicables."},
            {"id":3,"title":"Pregunta qué quieres llevar","action":"Escribe cualquier artículo o mercancía que quieras consultar."},
            {"id":4,"title":"Comprueba las reglas oficiales","action":"Revisa la fuente oficial indicada antes de viajar."},
            {"id":5,"title":"Guarda tu resumen","action":"Conserva tu información de preparación."}
        ]
    }

@app.get("/api/cuba")
async def cuba():
    return {
        "status":"ok",
        "destination":"Cuba",
        "official_sources":[
            OFFICIAL_SOURCES["aduana_cuba"],
            OFFICIAL_SOURCES["dviajeros"],
            OFFICIAL_SOURCES["evisa"]
        ],
        "message":(
            "Para viajar a Cuba deben revisarse por separado los procesos "
            "de viaje, documentación, D'Viajeros, eVisa cuando corresponda, "
            "equipaje y las reglas de entrada de Aduana."
        )
    }

@app.get("/api/documents")
async def documents():
    return {
        "status":"ok",
        "title":"Documentos y procesos oficiales",
        "sources":[
            OFFICIAL_SOURCES["dviajeros"],
            OFFICIAL_SOURCES["evisa"],
            OFFICIAL_SOURCES["aduana_cuba"]
        ]
    }

@app.get("/api/practice")
async def practice():
    return {
        "status":"ok",
        "title":"Práctica guiada",
        "message":"Las simulaciones sirven para practicar antes de utilizar los sitios oficiales.",
        "official_sources":[
            OFFICIAL_SOURCES["dviajeros"],
            OFFICIAL_SOURCES["evisa"]
        ]
    }

@app.get("/api/simulations")
async def simulations():
    return {
        "status":"ok",
        "simulations":[
            {
                "id":"dviajeros",
                "name":"Práctica D'Viajeros",
                "url":OFFICIAL_SOURCES["dviajeros"]["url"]
            },
            {
                "id":"evisa",
                "name":"Práctica eVisa",
                "url":OFFICIAL_SOURCES["evisa"]["url"]
            },
            {
                "id":"flight",
                "name":"Práctica de búsqueda de vuelo",
                "url":"https://www.google.com/travel/flights"
            }
        ]
    }

@app.get("/api/baggage")
async def baggage():
    return {
        "status":"ok",
        "message":(
            "Las reglas de equipaje dependen del transportista y del tipo "
            "de artículo. Comprueba siempre la política oficial de la "
            "aerolínea antes de viajar."
        ),
        "airlines":AIRLINES
    }

@app.get("/api/flight")
async def flight():
    return {
        "status":"ok",
        "message":"Consulta las opciones de vuelo directamente con la aerolínea o mediante el buscador indicado.",
        "sources":[
            OFFICIAL_SOURCES["google_flights"],
            OFFICIAL_SOURCES["aa"],
            OFFICIAL_SOURCES["delta"],
            OFFICIAL_SOURCES["united"],
            OFFICIAL_SOURCES["southwest"],
            OFFICIAL_SOURCES["jetblue"]
        ]
    }

@app.get("/api/health/full")
async def health_full():
    return {
        "status":"ok",
        "app":APP_NAME,
        "company":COMPANY,
        "version":APP_VERSION,
        "static_index":INDEX_FILE.exists(),
        "static_directory":STATIC_DIR.exists(),
        "gemini_configured":bool(GEMINI_API_KEY),
        "gemini_model":GEMINI_MODEL if GEMINI_API_KEY else "",
        "official_sources":len(OFFICIAL_SOURCES),
        "airlines":len(AIRLINES)
    }
