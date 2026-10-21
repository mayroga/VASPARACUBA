from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
import json
import os

app = FastAPI()

# Configuración apuntando a la carpeta 'templates'
templates = Jinja2Templates(directory="templates")

def load_database():
    categories = {
        "Riddles & Discoveries": [],
        "Real-Life Situations": [],
        "Everyday Math & Problem Solving": [],
        "Human Needs & Positive Perspectives": []
    }
    
    if not os.path.exists("database.json"):
        return categories

    try:
        with open("database.json", "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return categories

    # Intento 1: Leer como un JSON estándar único
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if "categories" in data:
                return data["categories"]
            elif "batch" in data and "categories" in data:
                for cat, items in data["categories"].items():
                    if cat in categories and isinstance(items, list):
                        categories[cat].extend(items)
                return categories
    except json.JSONDecodeError:
        pass

    # Intento 2: Si hay múltiples objetos JSON concatenados o bloques por lotes
    decoder = json.JSONDecoder()
    pos = 0
    text_len = len(text)
    while pos < text_len:
        while pos < text_len and text[pos].isspace():
            pos += 1
        if pos >= text_len:
            break
        try:
            obj, idx = decoder.raw_decode(text, pos)
            pos = idx
            if isinstance(obj, dict):
                cats = obj.get("categories", obj)
                if isinstance(cats, dict):
                    for cat, items in cats.items():
                        if cat not in categories:
                            categories[cat] = []
                        if isinstance(items, list):
                            categories[cat].extend(items)
        except json.JSONDecodeError:
            pos += 1  # Salta caracteres inválidos para continuar
            
    return categories

# Cargar la base de datos al iniciar la aplicación
DATABASE = load_database()

@app.get("/")
def home(request: Request):
    # Renderiza templates/index.html correctamente
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
def status():
    return {"message": "API Activa", "database_loaded": bool(DATABASE)}

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
