import json
import random
import logging
from pathlib import Path
from copy import deepcopy

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

# --------------------------------------------------
# WE SELL TIME — CONFIGURACIÓN PRINCIPAL
# --------------------------------------------------

app = FastAPI(title="WE SELL TIME")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_FILE = BASE_DIR / "cards_bilingual.json"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("we_sell_time")

DEFAULT_CATEGORIES = [
    "Riddles & Discoveries",
    "Real-Life Situations",
    "Everyday Math & Problem Solving",
    "Human Needs & Positive Perspectives",
]

# --------------------------------------------------
# EJERCICIOS OPCIONALES DE 40–45 SEGUNDOS
# --------------------------------------------------

DEFAULT_EXERCISES = [
    {
        "id": "natural_breathing",
        "duration_seconds": 45,
        "type": "breathing",
        "title": {
            "en": "Natural breathing",
            "es": "Respiración natural",
        },
        "instructions": {
            "en": (
                "Sit comfortably. Breathe naturally and gently. "
                "Do not hold your breath or force deep breaths. "
                "Stop if you feel dizzy or uncomfortable."
            ),
            "es": (
                "Siéntate cómodamente. Respira de forma natural y suave. "
                "No retengas el aire ni fuerces respiraciones profundas. "
                "Detente si sientes mareo o incomodidad."
            ),
        },
    },
    {
        "id": "shoulder_release",
        "duration_seconds": 45,
        "type": "gentle_movement",
        "title": {
            "en": "Shoulder release",
            "es": "Relaja los hombros",
        },
        "instructions": {
            "en": (
                "If comfortable, gently lift your shoulders, then let "
                "them drop and relax. Repeat slowly. You can skip the "
                "movement and simply rest."
            ),
            "es": (
                "Si te resulta cómodo, eleva suavemente los hombros "
                "y después déjalos bajar y relajarse. Repite despacio. "
                "Puedes omitir el movimiento y simplemente descansar."
            ),
        },
    },
    {
        "id": "hand_wake_up",
        "duration_seconds": 40,
        "type": "gentle_movement",
        "title": {
            "en": "Wake up your hands",
            "es": "Activa las manos",
        },
        "instructions": {
            "en": (
                "Slowly open and close your fingers, then relax your "
                "hands. Keep the movement easy and pain-free."
            ),
            "es": (
                "Abre y cierra lentamente los dedos y después relaja "
                "las manos. Haz movimientos cómodos y sin dolor."
            ),
        },
    },
    {
        "id": "rest_the_eyes",
        "duration_seconds": 45,
        "type": "passive_rest",
        "title": {
            "en": "Rest your eyes",
            "es": "Descansa la vista",
        },
        "instructions": {
            "en": (
                "Look away from the screen at a comfortable distance. "
                "Let your face and jaw relax and rest your eyes "
                "without straining."
            ),
            "es": (
                "Aparta la mirada de la pantalla y mira a una distancia "
                "cómoda. Relaja el rostro y la mandíbula y descansa "
                "la vista sin esfuerzo."
            ),
        },
    },
]

DEFAULT_SAFETY = {
    "en": (
        "These are optional comfort breaks, not medical treatment. "
        "Stay seated if preferred. Skip any uncomfortable movement "
        "and stop if you feel pain, dizziness, or shortness of breath."
    ),
    "es": (
        "Estas son pausas opcionales de comodidad, no tratamientos "
        "médicos. Puedes permanecer sentado. Omite cualquier movimiento "
        "incómodo y detente si sientes dolor, mareo o falta de aire."
    ),
}


# --------------------------------------------------
# CARGA Y VALIDACIÓN DEL JSON
# --------------------------------------------------

def load_database():
    if not DATA_FILE.is_file():
        logger.error("No se encontró el archivo: %s", DATA_FILE)
        return [], {
            "easy_reset_exercises": DEFAULT_EXERCISES,
            "safety_notes": DEFAULT_SAFETY,
            "target_session_seconds": 300,
        }

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            questions = data
            config = {}

        elif isinstance(data, dict):
            config = dict(data.get("app_config") or {})

            if isinstance(data.get("questions"), list):
                questions = data["questions"]
            else:
                categories = data.get("categories", data)
                questions = []

                if isinstance(categories, dict):
                    for category, items in categories.items():
                        if not isinstance(items, list):
                            continue

                        for item in items:
                            if not isinstance(item, dict):
                                continue

                            # Ignorar bloques de configuración.
                            if category == "app_config":
                                continue

                            question = dict(item)
                            question.setdefault("topic", category)
                            questions.append(question)
        else:
            logger.error("El formato principal del JSON no es válido.")
            questions = []
            config = {}

        valid_questions = []

        for question in questions:
            if not isinstance(question, dict):
                continue

            if not isinstance(question.get("en"), dict):
                continue

            if not isinstance(question.get("es"), dict):
                continue

            # Evitar modificar los datos originales cargados.
            question = deepcopy(question)

            # Aceptar preguntas que tengan texto en ambos idiomas.
            if not question["en"].get("prompt"):
                continue

            if not question["es"].get("prompt"):
                continue

            valid_questions.append(question)

        exercises = config.get("easy_reset_exercises")
        if not isinstance(exercises, list):
            exercises = DEFAULT_EXERCISES

        safety_notes = config.get("safety_notes")
        if not isinstance(safety_notes, dict):
            safety_notes = DEFAULT_SAFETY

        session_seconds = config.get("target_session_seconds", 300)
        try:
            session_seconds = int(session_seconds)
        except (TypeError, ValueError):
            session_seconds = 300

        # Mantener una sesión de cinco minutos por defecto.
        if session_seconds <= 0:
            session_seconds = 300

        normalized_config = {
            "easy_reset_exercises": exercises,
            "safety_notes": safety_notes,
            "target_session_seconds": session_seconds,
        }

        logger.info(
            "JSON cargado: %s preguntas y %s ejercicios.",
            len(valid_questions),
            len(exercises),
        )

        return valid_questions, normalized_config

    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("No se pudo leer el JSON: %s", exc)

    except Exception as exc:
        logger.exception("Error inesperado al cargar el JSON: %s", exc)

    return [], {
        "easy_reset_exercises": DEFAULT_EXERCISES,
        "safety_notes": DEFAULT_SAFETY,
        "target_session_seconds": 300,
    }


QUESTIONS, APP_CONFIG = load_database()

EXERCISES = APP_CONFIG["easy_reset_exercises"]
SAFETY_NOTES = APP_CONFIG["safety_notes"]


# --------------------------------------------------
# MEZCLAR OPCIONES SIN PERDER LA RESPUESTA CORRECTA
# --------------------------------------------------

def shuffle_localized_options(localized):
    """
    Mezcla las opciones de un idioma.

    Conserva la respuesta correcta cuando está expresada como texto.
    Si correct_answer es un índice numérico, actualiza el índice
    para que continúe señalando la opción correcta.
    """
    localized = deepcopy(localized)

    options = localized.get("options")

    if not isinstance(options, list) or len(options) < 2:
        return localized

    correct_answer = localized.get("correct_answer")

    # Distinguir un índice entero de una respuesta textual.
    is_index = (
        isinstance(correct_answer, int)
        and not isinstance(correct_answer, bool)
    )

    correct_text = None

    if is_index and 0 <= correct_answer < len(options):
        correct_text = options[correct_answer]

    shuffled_options = list(options)
    random.shuffle(shuffled_options)

    localized["options"] = shuffled_options

    if is_index and correct_text is not None:
        localized["correct_answer"] = shuffled_options.index(correct_text)

    return localized


def copy_and_shuffle_options(question):
    card = deepcopy(question)

    for language in ("en", "es"):
        localized = card.get(language)

        if isinstance(localized, dict):
            card[language] = shuffle_localized_options(localized)

    return card


# --------------------------------------------------
# PÁGINA PRINCIPAL
# --------------------------------------------------

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


# --------------------------------------------------
# ESTADO DE LA APLICACIÓN
# --------------------------------------------------

@app.get("/api/status")
def status():
    return {
        "message": "API Activa",
        "database_loaded": len(QUESTIONS) > 0,
        "total_cards_loaded": len(QUESTIONS),
        "categories": sorted({
            question.get("topic", "General")
            for question in QUESTIONS
        }),
        "exercises_loaded": len(EXERCISES),
        "session_seconds": APP_CONFIG["target_session_seconds"],
        "data_file": DATA_FILE.name,
    }


# --------------------------------------------------
# SESIÓN DE CINCO MINUTOS
# --------------------------------------------------

@app.get("/api/session")
def create_session():
    questions = list(QUESTIONS)
    random.shuffle(questions)

    exercises = deepcopy(EXERCISES)
    random.shuffle(exercises)

    return {
        "questions": [
            copy_and_shuffle_options(question)
            for question in questions
        ],
        "exercises": exercises,
        "safety_notes": SAFETY_NOTES,
        "session_seconds": APP_CONFIG["target_session_seconds"],
    }


# --------------------------------------------------
# API ANTERIOR: COMPATIBILIDAD CON EL HTML EXISTENTE
# --------------------------------------------------

@app.post("/api/next-card")
async def next_card(request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = {}
    except Exception:
        body = {}

    index = body.get("index")

    # Modo de navegación por índice.
    if isinstance(index, int) and not isinstance(index, bool):
        if 0 <= index < len(QUESTIONS):
            return copy_and_shuffle_options(QUESTIONS[index])

        return {
            "message": "Completed",
            "finished": True,
        }

    # Modo de navegación por categoría.
    indices = body.get("indices", {})
    if not isinstance(indices, dict):
        indices = {}

    for category in DEFAULT_CATEGORIES:
        category_questions = [
            question for question in QUESTIONS
            if question.get("topic") == category
        ]

        try:
            category_index = int(indices.get(category, 0) or 0)
        except (TypeError, ValueError):
            category_index = 0

        if 0 <= category_index < len(category_questions):
            card = copy_and_shuffle_options(
                category_questions[category_index]
            )

            next_indices = dict(indices)
            next_indices[category] = category_index + 1
            card["next_indices"] = next_indices

            return card

    return {
        "message": "Completed",
        "finished": True,
    }


# --------------------------------------------------
# COMPROBACIÓN BÁSICA DE SALUD DEL SERVIDOR
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "database_loaded": len(QUESTIONS) > 0,
    }
