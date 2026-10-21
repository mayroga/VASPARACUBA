from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import os

app = FastAPI(title="WE SELL TIME")
templates = Jinja2Templates(directory=".")

DATA_FILE = "cards_bilingual.json"

def load_database():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)["categories"]
    return {}

DATABASE = load_database()

class UserSessionState(BaseModel):
    indices: dict = {
        "Riddles & Discoveries": 0,
        "Real-Life Situations": 0,
        "Everyday Math & Problem Solving": 0,
        "Human Needs & Positive Perspectives": 0
    }

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/next-card")
async def get_next_card(state: UserSessionState):
    category_keys = [k for k, v in DATABASE.items() if len(v) > 0]
    if not category_keys:
        return {"error": "No content available"}

    total_seen = sum(state.indices.values())
    current_cat = category_keys[total_seen % len(category_keys)]

    items = DATABASE[current_cat]
    current_index = state.indices.get(current_cat, 0)
    card = items[current_index]

    state.indices[current_cat] = (current_index + 1) % len(items)

    response_data = {
        "category": current_cat,
        "en": card["en"],
        "es": card["es"],
        "next_indices": state.indices
    }
    return response_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
