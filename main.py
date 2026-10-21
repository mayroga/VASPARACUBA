from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def load_database():
    categories = {
        "Riddles & Discoveries": [],
        "Real-Life Situations": [],
        "Everyday Math & Problem Solving": [],
        "Human Needs & Positive Perspectives": []
    }
    
    try:
        with open("database.json", "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return categories

    # Intento 1: Leer como un JSON estándar único
    try:
        data = json.loads(text)
        if "categories" in data:
            return data["categories"]
        elif isinstance(data, dict) and "batch" in data and "categories" in data:
            for cat, items in data["categories"].items():
                if cat in categories:
                    categories[cat].extend(items)
            return categories
    except json.JSONDecodeError:
        pass

    # Intento 2: Si hay múltiples objetos JSON concatenados
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
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
            pos += 1
            
    return categories

DATABASE = load_database()

@app.get("/")
def home(request: Request):
    return {"message": "API Activa", "database_loaded": bool(DATABASE)}
