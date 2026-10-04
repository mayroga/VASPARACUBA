# main.py — ¿QUÉ QUIERES LLEVAR? | May Roga LLC
from __future__ import annotations
import os,re,json
from pathlib import Path
from typing import Any,Optional
import httpx
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field

APP_VERSION="11.0.0"
BASE_DIR=Path(__file__).resolve().parent
STATIC_DIR=BASE_DIR/"static"
INDEX_FILE=STATIC_DIR/"index.html"
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","").strip()
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash").strip()

app=FastAPI(title="¿QUÉ QUIERES LLEVAR? | May Roga LLC",version=APP_VERSION)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])

if STATIC_DIR.exists():
    app.mount("/static",StaticFiles(directory=str(STATIC_DIR)),name="static")

class ItemCheckRequest(BaseModel):
    item_name:str=Field(...,min_length=1,max_length=300)
    destination:str="Cuba"
    luggage_type:str="mano"
    origin:str=""
    airline:str=""
    context:str=""

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
"aduana":{"name":"Aduana General de la República de Cuba","url":"https://www.aduana.gob.cu/"},
"dviajeros":{"name":"D’Viajeros","url":"https://dviajeros.mitrans.gob.cu/"},
"evisa":{"name":"eVisa Cuba","url":"https://evisacuba.cu/"},
"flights":{"name":"Google Flights","url":"https://www.google.com/travel/flights"}
}

def clean_text(value:Any)->str:
    return re.sub(r"\s+"," ",str(value or "")).strip()

def source_for_destination(destination:str)->dict:
    if "cuba" in clean_text(destination).lower():
        return OFFICIAL_SOURCES["aduana"]
    return {"name":"Autoridad aduanera del destino","url":"https://www.google.com/"}

def local_item_check(item:str,destination:str,luggage_type:str)->dict:
    q=clean_text(item).lower()
    dest=clean_text(destination) or "Cuba"
    cuba="cuba" in dest.lower()
    src=source_for_destination(dest)
    base={"article":item,"what_matters":[],"questions_to_confirm":[],"official_sources":[src]}
    if not q:
        return {**base,"status":"REVISA ESTO ANTES DE VIAJAR","recommendation":"Escribe el nombre del artículo para poder orientarte."}

    if any(x in q for x in ["arma","pistola","rifle","munición","municion","explosivo","granada"]):
        return {**base,"status":"NO LO DES POR PERMITIDO","recommendation":"Este artículo puede estar sujeto a controles o restricciones especiales. No lo transportes sin confirmarlo expresamente con la autoridad y la aerolínea.","what_matters":["tipo exacto","finalidad","forma de transporte"],"questions_to_confirm":["¿Cuál es el artículo exacto y su modelo?","¿Lo llevarás en equipaje o mediante otro tipo de transporte?"]}

    if any(x in q for x in ["power bank","batería externa","bateria externa","estación de energía","estacion de energia","power station","energy station","batería de litio","bateria de litio","batería","bateria"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Las baterías pueden tener reglas específicas de transporte. La respuesta puede cambiar según el tipo de batería, capacidad, peso, si es una batería instalada o suelta y dónde viajará. No des por permitido el artículo sin comprobar esos datos con la aerolínea y la autoridad correspondiente.","what_matters":["tipo de batería","capacidad en Wh","peso","batería instalada o suelta","cabina o equipaje facturado"],"questions_to_confirm":["¿Cuántos Wh indica la etiqueta?","¿Qué tipo de batería utiliza?","¿Cuál es el peso?","¿La batería se puede retirar?"]}

    if any(x in q for x in ["automóvil","automovil","carro","auto","coche","vehículo","vehiculo"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Un automóvil no debe tratarse automáticamente como equipaje de pasajero. Hay que distinguir entre transportar el vehículo como carga, enviarlo por otra vía o simplemente viajar con alguna pieza del vehículo. La respuesta depende del tipo de transporte y de las reglas aduaneras aplicables.","what_matters":["vehículo completo o pieza","método de transporte","modelo","año","valor","combustible y batería"],"questions_to_confirm":["¿Quieres llevar el vehículo completo o una pieza?","¿Lo transportarías como carga o equipaje?","¿Cuál es la marca, modelo y año?"]}

    if any(x in q for x in ["motocicleta","moto","motorcycle","scooter","patineta","patinete","bicicleta eléctrica","bicicleta electrica","e-bike","ebike"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Los vehículos pequeños y eléctricos no deben tratarse todos de la misma manera. Si tiene batería, esa batería puede cambiar completamente las condiciones de transporte. También importan el tamaño, peso y forma de transporte.","what_matters":["si tiene batería","tipo y capacidad de batería","peso","dimensiones","batería desmontable","equipaje o carga"],"questions_to_confirm":["¿Es eléctrica o de combustible?","¿Qué capacidad tiene la batería en Wh, si tiene batería?","¿Cuál es el peso?","¿La batería se puede retirar?"]}

    if any(x in q for x in ["bicicleta","bike"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Una bicicleta puede estar sujeta a condiciones específicas de transporte según la aerolínea, tamaño, peso y forma de embalaje. Si es eléctrica, la batería añade reglas adicionales.","what_matters":["peso","dimensiones","embalaje","eléctrica o convencional","batería"],"questions_to_confirm":["¿Es eléctrica?","¿Cuánto pesa?","¿La batería se puede retirar?"]}

    if any(x in q for x in ["motor","motor de carro","motor de auto","engine","alternador","bomba","repuesto","repuestos","pieza","piezas","autoparte","autopartes"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Las piezas y motores pueden tener condiciones distintas según tamaño, peso, materiales y características internas. No asumas que un repuesto puede viajar como equipaje normal.","what_matters":["tipo de pieza","peso","dimensiones","líquidos o combustible","batería","forma de transporte"],"questions_to_confirm":["¿Qué pieza o motor es exactamente?","¿Tiene combustible, aceite u otro líquido?","¿Cuál es su peso y tamaño?"]}

    if any(x in q for x in ["medicamento","medicina","pastilla","antibiótico","antibiotico","insulina","jeringa"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Los medicamentos pueden estar sujetos a condiciones que dependen del producto, cantidad, presentación y finalidad. Para un medicamento específico, confirma directamente la fuente oficial correspondiente.","what_matters":["nombre exacto","cantidad","presentación","uso personal o no"],"questions_to_confirm":["¿Cuál es el nombre exacto del medicamento?","¿Cuánta cantidad llevas?","¿Es para uso personal?"]}

    if any(x in q for x in ["perfume","colonia","shampoo","champú","crema","loción","locion","gel","líquido","liquido","cosmético","cosmetico","aerosol"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Los líquidos, aerosoles y geles pueden tener condiciones diferentes según el tipo de equipaje y los controles de seguridad. Confirma el envase, cantidad y forma de transporte.","what_matters":["tipo de producto","cantidad","tamaño del envase","cabina o facturado"],"questions_to_confirm":["¿Cuánto contiene el envase?","¿Lo llevarás en cabina o facturado?"]}

    if any(x in q for x in ["celular","teléfono","telefono","iphone","android","laptop","computadora","ordenador","tablet","ipad","cámara","camara","electrónico","electronico"]):
        return {**base,"status":"PUEDE SER POSIBLE, PERO DEBES CONFIRMAR","recommendation":"Los equipos electrónicos suelen poder transportarse, pero la batería y las condiciones de la aerolínea pueden cambiar la forma correcta de llevarlos. Confirma las instrucciones de la aerolínea que opera tu vuelo.","what_matters":["batería","peso","tamaño","cabina o facturado"],"questions_to_confirm":["¿Tiene batería de litio?","¿Cuál es el modelo si se trata de un equipo especial?"]}

    if any(x in q for x in ["ropa","camisa","pantalón","pantalon","vestido","abrigo","zapatos","tenis","sandalias","ropa interior"]):
        return {**base,"status":"REVISA CANTIDAD Y CONDICIONES","recommendation":"La ropa y el calzado forman parte normalmente de las pertenencias del viajero, pero la cantidad, peso, volumen y tratamiento aduanero pueden cambiar según las circunstancias.","what_matters":["cantidad","peso","uso personal o comercial"],"questions_to_confirm":["¿Es para uso personal?","¿Llevas una cantidad fuera de lo habitual?"]}

    if any(x in q for x in ["arroz","frijol","frijoles","café","cafe","galletas","conserva","conservas","comida","alimento","alimentos","chocolate","dulce","caramelo","pasta","harina","azúcar","azucar"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Los alimentos no tienen todos la misma regla. El producto exacto, su origen, presentación, cantidad y condiciones sanitarias pueden cambiar la respuesta. Confirma el producto específico antes de empacarlo.","what_matters":["producto exacto","origen","presentación","cantidad","condición sanitaria"],"questions_to_confirm":["¿Qué alimento es exactamente?","¿Está procesado o fresco?","¿Qué cantidad llevas?"]}

    if any(x in q for x in ["carne","pollo","cerdo","res","pescado","marisco","embutido","queso","leche","huevo"]):
        return {**base,"status":"NO LO DES POR PERMITIDO","recommendation":"Los productos de origen animal pueden estar sujetos a controles sanitarios y restricciones especiales. Confirma el producto exacto con la autoridad correspondiente antes de viajar.","what_matters":["tipo de producto","origen","procesamiento","cantidad","condición sanitaria"],"questions_to_confirm":["¿Qué producto es exactamente?","¿Está fresco, congelado, cocido o procesado?"]}

    if any(x in q for x in ["herramienta","martillo","taladro","destornillador","sierra","cuchillo","navaja","alicate","llave"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Las herramientas pueden tener condiciones diferentes en cabina y equipaje facturado. La respuesta depende del objeto exacto y de las reglas de seguridad de la aerolínea y del aeropuerto.","what_matters":["tipo de herramienta","tamaño","cabina o facturado"],"questions_to_confirm":["¿Qué herramienta es exactamente?","¿En qué tipo de equipaje quieres llevarla?"]}

    if any(x in q for x in ["electrodoméstico","electrodomestico","ventilador","microondas","licuadora","refrigerador","nevera","televisor","televisión","television","aire acondicionado","lavadora"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Un equipo grande puede estar condicionado por peso, dimensiones, cantidad, valor y forma de transporte. No asumas que puede viajar como equipaje normal.","what_matters":["peso","dimensiones","cantidad","valor","tipo de transporte"],"questions_to_confirm":["¿Qué equipo es exactamente?","¿Cuánto pesa y mide?"]}

    if any(x in q for x in ["dinero","efectivo","cash","moneda","dólares","dolares"]):
        return {**base,"status":"REQUIERE REVISIÓN","recommendation":"Las reglas sobre dinero y declaración pueden depender del destino y de la cantidad. No damos una cifra sin comprobar la normativa vigente.","what_matters":["tipo de dinero","cantidad","país de salida y destino"],"questions_to_confirm":["¿Qué cantidad quieres transportar?","¿En qué moneda?"]}

    return {**base,"status":"NECESITAMOS COMPROBARLO","recommendation":f"No tenemos información suficiente para afirmar si «{item}» está permitido o prohibido. Eso no significa ninguna de las dos cosas. Lo correcto es identificar el artículo exacto y comprobar la regla oficial aplicable.","what_matters":["artículo exacto","cantidad","peso y dimensiones","forma de transporte"],"questions_to_confirm":["¿Cuál es el modelo o descripción exacta?","¿Qué cantidad llevas?","¿Quieres llevarlo en cabina, facturado o como carga?"]}

def parse_gemini_text(data:dict)->str:
    try:
        return "\n".join(str(p.get("text","")) for p in data.get("candidates",[{}])[0].get("content",{}).get("parts",[]) if p.get("text")).strip()
    except Exception:
        return ""

def extract_json(text:str)->Optional[dict]:
    if not text:return None
    text=text.strip()
    text=re.sub(r"^```(?:json)?\s*","",text,flags=re.I)
    text=re.sub(r"\s*```$","",text)
    try:
        obj=json.loads(text)
        return obj if isinstance(obj,dict) else None
    except Exception:
        m=re.search(r"\{.*\}",text,re.S)
        if m:
            try:
                obj=json.loads(m.group(0))
                return obj if isinstance(obj,dict) else None
            except Exception:
                return None
    return None

def normalize_ai_answer(data:dict,item:str,destination:str)->dict:
    fallback=local_item_check(item,destination,"")
    if not isinstance(data,dict):return fallback
    status=clean_text(data.get("status")) or "NECESITAMOS COMPROBARLO"
    recommendation=clean_text(data.get("recommendation") or data.get("message"))
    article=clean_text(data.get("article")) or item
    matters=data.get("what_matters")
    questions=data.get("questions_to_confirm")
    sources=data.get("official_sources")
    if not recommendation:return fallback
    if not isinstance(matters,list):matters=[]
    if not isinstance(questions,list):questions=[]
    if not isinstance(sources,list):sources=[]
    clean_sources=[]
    for s in sources:
        if isinstance(s,dict):
            name=clean_text(s.get("name"))
            url=clean_text(s.get("url"))
            if name and url and (url.startswith("https://") or url.startswith("http://")):
                clean_sources.append({"name":name,"url":url})
    if not clean_sources:
        clean_sources=fallback["official_sources"]
    return {
        "status":status,
        "article":article,
        "recommendation":recommendation,
        "what_matters":[clean_text(x) for x in matters if clean_text(x)][:8],
        "questions_to_confirm":[clean_text(x) for x in questions if clean_text(x)][:8],
        "official_sources":clean_sources
    }

async def ask_gemini(item:str,destination:str,luggage_type:str,origin:str="",airline:str="",context:str="")->Optional[dict]:
    if not GEMINI_API_KEY:return None
    cuba="cuba" in destination.lower()
    official="Aduana General de la República de Cuba: https://www.aduana.gob.cu/; D’Viajeros: https://dviajeros.mitrans.gob.cu/; eVisa Cuba: https://evisacuba.cu/" if cuba else "Indica la autoridad oficial correspondiente al destino y no inventes una URL."
    prompt=f"""
Eres el motor de análisis de artículos de la aplicación ¿QUÉ QUIERES LLEVAR? de May Roga LLC.

OBJETIVO:
Ayudar al usuario a entender QUÉ DEBE COMPROBAR antes de transportar un artículo.

DATOS:
Artículo: {item}
Destino: {destination}
Origen: {origin or "no indicado"}
Tipo de equipaje: {luggage_type or "no indicado"}
Aerolínea: {airline or "no indicada"}
Contexto: {context or "no indicado"}

REGLAS OBLIGATORIAS:
1. NO INVENTES. Está prohibido inventar leyes, prohibiciones, permisos, cantidades, límites de peso, límites de Wh, tarifas, impuestos, horarios, disponibilidad o requisitos.
2. No conviertas una suposición en una regla.
3. Si no puedes respaldar una afirmación con una fuente oficial aplicable, no la presentes como hecho.
4. Diferencia entre seguridad de transporte/aerolínea y aduana/importación.
5. Si el artículo puede cambiar de tratamiento por batería, Wh, peso, dimensiones, combustible, líquido, presión, cantidad, modelo, valor, origen, embalaje o tipo de equipaje, indícalo.
6. Si falta un dato que realmente cambia la respuesta, pregunta solamente por ese dato.
7. Si no hay información suficiente, NO digas simplemente "sí" o "no". Di que requiere comprobación y explica exactamente dónde debe mirar el usuario.
8. Para vehículos, motores, baterías, estaciones de energía, bicicletas eléctricas, motocicletas, patinetas eléctricas, repuestos y artículos grandes, analiza las características que pueden cambiar el tratamiento.
9. Para Cuba, separa claramente las cuestiones aduaneras de las reglas de la aerolínea.
10. Usa fuentes oficiales. No uses blogs, foros, TikTok, Reddit ni páginas comerciales como autoridad.
11. Si una fuente oficial no confirma el punto, dilo.
12. Nunca solicites contraseñas, CVV, códigos de seguridad, datos bancarios ni credenciales.
13. Habla en español sencillo, tranquilo y resolutivo.
14. El usuario debe terminar sabiendo qué hacer a continuación.
15. Si solo puedes dar una orientación preliminar, dilo claramente.
16. Fuentes oficiales conocidas para Cuba: {official}

IMPORTANTE:
No afirmes que una regla está vigente solamente porque la recuerdes.
Cuando una regla dependa de una aerolínea concreta, manda al usuario a la política oficial de la aerolínea que opera su vuelo.
Cuando dependa de Aduana de Cuba, manda al usuario a Aduana.
Cuando dependa de D’Viajeros, manda a D’Viajeros.
Cuando corresponda a eVisa, manda a eVisa.

DEVUELVE ÚNICAMENTE JSON VÁLIDO, SIN MARKDOWN:
{{
 "status":"...",
 "article":"...",
 "recommendation":"...",
 "what_matters":["..."],
 "questions_to_confirm":["..."],
 "official_sources":[{{"name":"...","url":"https://..."}}]
}}

STATUS debe ser uno de estos:
"SE PUEDE ORIENTAR"
"PUEDE SER POSIBLE, PERO DEBES CONFIRMAR"
"REQUIERE REVISIÓN"
"NO LO DES POR PERMITIDO"
"NECESITAMOS COMPROBARLO"

    url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload={
        "contents":[{"role":"user","parts":[{"text":prompt}]}],
        "generationConfig":{"temperature":0.1,"maxOutputTokens":1000,"responseMimeType":"application/json"}
    }
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            r=await client.post(url,params={"key":GEMINI_API_KEY},json=payload)
        if r.status_code!=200:return None
        raw=parse_gemini_text(r.json())
        parsed=extract_json(raw)
        return normalize_ai_answer(parsed,item,destination) if parsed else None
    except Exception:
        return None

@app.get("/",response_class=HTMLResponse)
async def root():
    if INDEX_FILE.exists():return FileResponse(str(INDEX_FILE),media_type="text/html")
    return HTMLResponse("<h1>¿QUÉ QUIERES LLEVAR?</h1><p>No se encontró static/index.html.</p>")

@app.get("/api/health")
async def health():
    return {"status":"ok","app":"¿QUÉ QUIERES LLEVAR?","version":APP_VERSION,"gemini_configured":bool(GEMINI_API_KEY),"gemini_model":GEMINI_MODEL,"static_exists":STATIC_DIR.exists(),"index_exists":INDEX_FILE.exists()}

@app.post("/api/check-item")
async def check_item(request:ItemCheckRequest):
    item=clean_text(request.item_name)
    destination=clean_text(request.destination) or "Cuba"
    luggage=clean_text(request.luggage_type) or "No indicado"
    if not item:raise HTTPException(status_code=400,detail="Debes indicar un artículo.")
    ai=await ask_gemini(item,destination,luggage,clean_text(request.origin),clean_text(request.airline),clean_text(request.context))
    result=ai or local_item_check(item,destination,luggage)
    if not ai:
        result["ai_available"]=False
        result["notice"]="No se obtuvo una respuesta de Gemini. Se muestra orientación de respaldo y se recomienda confirmar en la fuente oficial."
    else:
        result["ai_available"]=True
    result["item"]=item
    result["destination"]=destination
    result["luggage_type"]=luggage
    return result

@app.get("/api/airlines")
async def airlines():
    return {"destination":"Cuba","notice":"Consulta cada sitio oficial para confirmar rutas, fechas, horarios, equipaje y disponibilidad.","google_flights":OFFICIAL_SOURCES["flights"],"airlines":AIRLINES}

@app.get("/api/dviajeros")
async def dviajeros():
    return {"name":"D’Viajeros","url":OFFICIAL_SOURCES["dviajeros"]["url"],"official":True,"notice":"El proceso real debe completarse directamente en el sitio oficial."}

@app.get("/api/evisa")
async def evisa():
    return {"name":"eVisa Cuba","url":OFFICIAL_SOURCES["evisa"]["url"],"official":True,"notice":"Consulta directamente el sitio oficial para conocer el proceso vigente."}

@app.get("/api/trip")
async def trip_info():
    return {"message":"La preparación del viaje se realiza en el navegador.","storage":"No se almacenan datos personales del viaje en el servidor mediante este endpoint."}

@app.post("/api/analyze-trip")
async def analyze_trip(request:TripAnalysisRequest):
    origin=clean_text(request.origin)
    destination=clean_text(request.destination)
    stops=clean_text(request.has_stops)
    if not origin or not destination:raise HTTPException(status_code=400,detail="Faltan origen o destino.")
    if stops in ["stops","Sí","Si","yes"]:
        explanation=f"Tu práctica es un viaje de {origin} a {destination} con conexión. Confirma qué aerolínea opera cada tramo y cómo se manejará el equipaje durante la conexión."
    else:
        explanation=f"Tu práctica es un viaje de {origin} a {destination}. Confirma directamente con la aerolínea las condiciones del boleto, equipaje y cualquier artículo especial."
    return {"origin":origin,"destination":destination,"explanation":explanation}

@app.post("/api/gemini")
async def gemini_proxy(request:GeminiRequest):
    if not GEMINI_API_KEY:raise HTTPException(status_code=503,detail="Gemini no está configurado en Render.")
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload={"contents":[{"role":"user","parts":[{"text":request.prompt}]}],"generationConfig":{"temperature":0.2,"maxOutputTokens":1000}}
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            r=await client.post(url,params={"key":GEMINI_API_KEY},json=payload)
        if r.status_code!=200:raise HTTPException(status_code=502,detail="El servicio de IA no respondió correctamente.")
        return {"ok":True,"text":parse_gemini_text(r.json())}
    except HTTPException:raise
    except Exception:raise HTTPException(status_code=502,detail="No fue posible consultar el servicio de IA.")

@app.get("/api/config")
async def config():
    return {"app_version":APP_VERSION,"gemini_configured":bool(GEMINI_API_KEY),"gemini_model":GEMINI_MODEL,"client_configuration":False}

@app.get("/api")
async def api_root():
    return {"app":"¿QUÉ QUIERES LLEVAR?","version":APP_VERSION,"endpoints":["/api/health","/api/check-item","/api/airlines","/api/dviajeros","/api/evisa","/api/analyze-trip","/api/trip"]}

@app.get("/favicon.ico")
async def favicon():
    return HTMLResponse("",status_code=204)

