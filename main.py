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

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clave de API de Gemini obtenida de las variables de entorno de Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class ItemCheckRequest(BaseModel):
    item_name: str
    destination: Optional[str] = "Cuba"
    luggage_type: Optional[str] = "mano" # mano, documentado

class TripAnalysisRequest(BaseModel):
    origin: str
    destination: str
    flight_type: str # directo, escala
    airline: Optional[str] = "General"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Devuelve la interfaz principal integrada
    return
    
Qu-Quieres-Llevar
Asesoría de Viaje Independiente - May Roga LLC

¿Qué artículo deseas consultar?
Escribe lo que quieres llevar para saber en qué maleta debe ir y si está permitido.

Ej. Perfume, Power Bank, Medicamentos...
 
Resultado de la Asesoría:
Aplicación informativa independiente de May Roga LLC. No representa a aerolíneas ni gobiernos.
