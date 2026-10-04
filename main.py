```python
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(
    title="Qu-Quieres-Llevar",
    description="Acompañante de preparación de viaje de May Roga LLC",
    version="1.0.0"
)

# Configuración de CORS conectada con los demás componentes del sistema
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clave de API de Gemini obtenida de la variable de entorno configurada en Render (render.yaml)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class ItemCheckRequest(BaseModel):
    item_name: str
    destination: Optional[str] = "Cuba"
    luggage_type: Optional[str] = "mano"

class TripAnalysisRequest(BaseModel):
    origin: str
    destination: str
    flight_type: str
    airline: Optional[str] = "General"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Renderiza la interfaz principal garantizando coherencia absoluta con el index.html y la filosofía de May Roga LLC
    return """
    

```

```
"""

```

@app.post("/api/check-item")
async def check_item(data: ItemCheckRequest):
item = data.item_name.lower()

```
# Integración con Gemini API para análisis inteligente de artículos y restricciones de viaje
if GEMINI_API_KEY:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{
                        "parts": [{"text": f"Analiza si el siguiente artículo '{item}' se puede llevar en equipaje de mano o documentado para viajar a Cuba, respondiendo brevemente en español con un estatus (PUEDES LLEVARLO, PUEDES LLEVARLO PERO..., NO PUEDES LLEVARLO) y una recomendación práctica humana."}]
                    }]
                },
                timeout=10.0
            )
            if response.status_code == 200:
                ai_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "status": "REVISA ESTO ANTES DE VIAJAR",
                    "recommendation": ai_text,
                    "source": "Fuentes Oficiales / Orientación May Roga"
                }
    except Exception:
        pass

# Reglas de respaldo predeterminadas para artículos comunes
if "bateria" in item or "power bank" in item:
    return {
        "status": "PUEDES LLEVARLO, PERO...",
        "recommendation": "Las baterías de litio y power banks obligatoriamente deben ir en tu equipaje de mano (maleta que sube contigo a la cabina). Está prohibido llevarlas en el equipaje documentado.",
        "source": "Normas internacionales de aviación civil"
    }
elif "perfume" in item or "liquido" in item:
    return {
        "status": "PUEDES LLEVARLO, PERO...",
        "recommendation": "Si lo llevas en la maleta de mano, los envases no deben superar los 100 ml (3.4 oz) y deben caber en una bolsa plástica transparente. Si es más grande, debe ir en el equipaje documentado.",
        "source": "Regulaciones de seguridad aeroportuaria"
    }
else:
    return {
        "status": "REVISA ESTO ANTES DE VIAJAR",
        "recommendation": f"Verifica que el artículo '{data.item_name}' cumpla con el peso y las dimensiones permitidas por tu aerolínea antes de empacarlo.",
        "source": "Guía general de May Roga LLC"
    }

```

@app.get("/api/health")
async def health_check():
return {"status": "healthy", "service": "Qu-Quieres-Llevar online"}

```

```
