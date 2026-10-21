from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import json
import os

app = FastAPI()

# Resolver rutas absolutas para evitar errores de despliegue (Internal Server Error)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
DATA_FILE = os.path.join(BASE_DIR, "cards_bilingual.json")

def load_database():
    categories = {
        "Riddles & Discoveries": [],
        "Real-Life Situations": [],
        "Everyday Math & Problem Solving": [],
        "Human Needs & Positive Perspectives": []
    }
    
    if not os.path.exists(DATA_FILE):
        print(f"ADVERTENCIA: No se encontró el archivo en {DATA_FILE}")
        return categories

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "categories" in data:
                return data["categories"]
    except Exception as e:
        print(f"Error al leer el JSON: {e}")
        
    return categories

DATABASE = load_database()

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
    
@app.get("/api/status")
def status():
    return {
        "message": "API Activa", 
        "database_loaded": bool(DATABASE),
        "total_categories": list(DATABASE.keys())
    }

@app.post("/api/next-card")
async def next_card(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
        
    indices = body.get("indices", {
        "Riddles & Discoveries": 0,
        "Real-Life Situations": 0,
        "Everyday Math & Problem Solving": 0,
        "Human Needs & Positive Perspectives": 0
    })
    
    categories_list = list(DATABASE.keys())
    
    for category in categories_list:
        items = DATABASE.get(category, [])
        idx = indices.get(category, 0)
        
        if items and idx < len(items):
            card = items[idx]
            next_indices = indices.copy()
            next_indices[category] = idx + 1
            
            return {
                "category": category,
                "id": card.get("id"),
                "en": card.get("en"),
                "es": card.get("es"),
                "next_indices": next_indices
            }
            
    return {"message": "Completed", "finished": True}
