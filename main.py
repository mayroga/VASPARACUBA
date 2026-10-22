import json
import random
import logging
from pathlib import Path
from copy import deepcopy

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

# WE SELL TIME
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

DEFAULT_SAFETY = {
    "en": (
        "Optional comfort break, not medical treatment. Breathe naturally "
        "without forcing deep breaths or holding your breath. Stay seated "
        "if preferred. Stop if you feel pain, dizziness, or shortness of breath."
    ),
    "es": (
        "Pausa opcional de comodidad, no tratamiento médico. Respira "
        "naturalmente, sin forzar respiraciones profundas ni retener el aire. "
        "Puedes permanecer sentado. Detente si sientes dolor, mareo o falta de aire."
    ),
}

# id, duración, título EN, título ES, instrucción EN, instrucción ES
EXERCISE_CONTENT = [
("soft_arrival",45,"Arrive gently","Llega con suavidad","Notice that you are here. Let your breathing find its own comfortable rhythm. There is nothing to achieve.","Nota que estás aquí. Deja que tu respiración encuentre su ritmo cómodo. No tienes nada que conseguir."),
("quiet_wave",45,"The quiet wave","La ola tranquila","Imagine a small wave arriving and leaving the shore. Let each natural breath remind you that moments can come and go.","Imagina una pequeña ola que llega a la orilla y se retira. Deja que cada respiración natural te recuerde que los momentos vienen y se van."),
("easy_exhale",40,"An easy exhale","Una exhalación tranquila","Breathe in comfortably. If it feels natural, let the breath out a little more slowly. Never push or empty your lungs forcefully.","Inhala cómodamente. Si te resulta natural, deja salir el aire un poco más despacio. No fuerces ni vacíes los pulmones."),
("nose_awareness",45,"Notice the air","Observa el aire","If comfortable, notice the air moving near your nose. There is no need to change your breathing. Simply observe a few breaths.","Si te resulta cómodo, nota el aire cerca de la nariz. No necesitas cambiar la respiración. Simplemente observa algunas respiraciones."),
("belly_softness",45,"A soft belly","Abdomen relajado","Allow your belly to remain soft. Let it move naturally as you breathe, without pushing it outward or pulling it inward.","Permite que tu abdomen permanezca relajado. Deja que se mueva naturalmente al respirar, sin empujarlo ni contraerlo."),
("chest_relax",45,"Relax the chest","Relaja el pecho","Release any unnecessary effort around your chest. Keep breathing comfortably and let your shoulders rest.","Suelta cualquier tensión innecesaria alrededor del pecho. Respira cómodamente y deja descansar los hombros."),
("breath_observer",40,"Be a breath observer","Observa tu respiración","Pretend you are a curious observer. Notice one breath, then another, without judging how deep, short, or long they are.","Imagina que eres un observador curioso. Nota una respiración y después otra, sin juzgar si son profundas, cortas o largas."),
("calm_cloud",45,"Clouds passing","Nubes que pasan","Picture a cloud crossing a wide sky. Let thoughts pass in the same way while you continue breathing naturally.","Imagina una nube cruzando un cielo amplio. Deja pasar los pensamientos de la misma manera mientras respiras naturalmente."),
("gentle_count",45,"Count a few breaths","Cuenta algunas respiraciones","Count each comfortable breath from one to four, then begin again if you wish. If you lose count, simply continue.","Cuenta cada respiración cómoda del uno al cuatro y vuelve a empezar si quieres. Si pierdes la cuenta, continúa sin preocuparte."),
("open_space",45,"Make room","Haz espacio","As you breathe, imagine there is a little more room around you. Relax your face and allow each breath to remain easy.","Mientras respiras, imagina que hay un poco más de espacio a tu alrededor. Relaja el rostro y respira sin esfuerzo."),
("shoulder_breath",40,"Shoulders at ease","Hombros tranquilos","Let your shoulders settle into a comfortable position. Breathe naturally and notice whether they can rest without effort.","Deja que tus hombros encuentren una posición cómoda. Respira naturalmente y observa si pueden descansar sin esfuerzo."),
("jaw_release",40,"Unclench the jaw","Relaja la mandíbula","Allow your teeth to separate slightly if comfortable. Soften your jaw and continue with quiet, natural breathing.","Si te resulta cómodo, separa ligeramente los dientes. Relaja la mandíbula y continúa respirando con naturalidad."),
("forehead_smooth",40,"A smoother forehead","Frente relajada","Let your forehead soften as if a small frown were melting away. There is no special breathing pattern to follow.","Relaja la frente como si un pequeño ceño se deshiciera. No necesitas seguir ningún patrón especial de respiración."),
("hands_at_rest",40,"Hands at rest","Manos en reposo","Rest your hands wherever they feel comfortable. Notice their contact with your lap or another surface while breathing normally.","Deja las manos donde estén cómodas. Nota su contacto con tus piernas o con otra superficie mientras respiras normalmente."),
("feet_on_ground",45,"Feel the ground","Siente el suelo","Notice your feet touching the floor. Feel the support beneath them and allow your breathing to continue at its natural pace.","Nota tus pies en contacto con el suelo. Siente el apoyo que reciben y deja que tu respiración mantenga su ritmo natural."),
("chair_support",45,"Supported by your seat","Apoyado en tu asiento","Feel the chair supporting your body. You do not need to hold yourself so rigidly. Settle comfortably and breathe naturally.","Siente cómo la silla sostiene tu cuerpo. No necesitas mantenerte tan rígido. Acomódate y respira naturalmente."),
("quiet_corner",45,"Your quiet corner","Tu rincón tranquilo","Imagine a peaceful corner where nothing needs your attention for a moment. Keep your eyes open or closed, as you prefer.","Imagina un rincón tranquilo donde nada necesite tu atención por un momento. Mantén los ojos abiertos o cerrados, como prefieras."),
("warm_sunlight",45,"Warm sunlight","Luz cálida del sol","Picture gentle sunlight falling across a familiar place. Let this pleasant image accompany a few comfortable breaths.","Imagina la luz suave del sol sobre un lugar conocido. Deja que esta imagen agradable acompañe algunas respiraciones cómodas."),
("forest_air",45,"A forest moment","Un momento en el bosque","Imagine standing among trees on a calm day. Notice the imagined freshness while breathing normally, without taking unusually deep breaths.","Imagina que estás entre árboles en un día tranquilo. Piensa en el aire fresco mientras respiras normalmente, sin inhalar exageradamente."),
("seaside_pause",45,"A seaside pause","Una pausa junto al mar","Picture the sea at a peaceful hour. Follow the imagined rhythm of the waves while allowing your own breathing to stay comfortable.","Imagina el mar en una hora tranquila. Sigue mentalmente el ritmo de las olas mientras mantienes una respiración cómoda."),
("rainy_window",45,"Rain on the window","Lluvia en la ventana","Imagine watching gentle rain through a window. There is nowhere you need to go in this moment. Let your breath remain natural.","Imagina que observas una lluvia suave desde una ventana. En este momento no necesitas ir a ningún sitio. Respira naturalmente."),
("garden_pause",45,"A garden pause","Pausa en un jardín","Picture a small garden with one detail you enjoy: a leaf, a flower, or a color. Return your attention to it whenever your mind wanders.","Imagina un pequeño jardín y un detalle que te guste: una hoja, una flor o un color. Vuelve a ese detalle cuando tu mente se distraiga."),
("mountain_view",45,"A wider view","Una vista más amplia","Imagine looking across a wide mountain landscape. Let the spacious view remind you that you can pause without solving everything now.","Imagina una vista amplia de montañas. Deja que ese paisaje te recuerde que puedes hacer una pausa sin resolverlo todo ahora."),
("floating_leaf",45,"A floating leaf","Una hoja flotando","Imagine a leaf floating gently on a stream. Watch it move in your mind while each breath comes and goes on its own.","Imagina una hoja flotando suavemente en un arroyo. Obsérvala mentalmente mientras cada respiración llega y se va por sí sola."),
("candle_glow",40,"A gentle glow","Un resplandor suave","Picture a small, steady light in a safe place. Let your attention rest there briefly, without changing your breathing.","Imagina una pequeña luz constante en un lugar seguro. Deja descansar allí tu atención por un momento, sin cambiar tu respiración."),
("favorite_place",45,"Visit a favorite place","Visita tu lugar favorito","Recall a place where you feel comfortable. Remember one color, one sound, and one detail while you breathe normally.","Recuerda un lugar donde te sientas cómodo. Evoca un color, un sonido y un detalle mientras respiras normalmente."),
("pleasant_memory",45,"A pleasant memory","Un recuerdo agradable","Bring to mind a small, pleasant memory. You do not need to relive the whole event; simply notice one detail that feels good.","Recuerda un momento pequeño y agradable. No necesitas revivir toda la experiencia; basta con observar un detalle que te haga sentir bien."),
("kind_inner_voice",45,"Speak kindly to yourself","Háblate con amabilidad","Silently tell yourself, I can take this moment slowly. Let those words accompany your natural breathing without demanding a particular feeling.","Dite en silencio: puedo tomarme este momento con calma. Deja que esas palabras acompañen tu respiración natural, sin exigirte sentir algo concreto."),
("permission_to_pause",40,"Permission to pause","Permiso para descansar","You are allowed to pause for a short moment. Nothing needs to be perfect. Let your breathing continue without trying to control it.","Tienes permiso para hacer una pausa breve. Nada tiene que ser perfecto. Deja que la respiración continúe sin intentar controlarla."),
("one_thing_less",45,"Put one thing down","Suelta una preocupación","Choose one small concern you can leave aside for these seconds. You do not have to solve it now. Return gently to your breathing.","Elige una preocupación pequeña que puedas dejar a un lado durante estos segundos. No tienes que resolverla ahora. Vuelve suavemente a tu respiración."),
("thoughts_on_train",45,"Thoughts on a train","Pensamientos en un tren","Imagine thoughts passing like train cars. You can notice them without climbing aboard. Let your attention return to the next natural breath.","Imagina que los pensamientos pasan como vagones de un tren. Puedes observarlos sin subirte. Vuelve a prestar atención a la siguiente respiración natural."),
("sound_and_breath",45,"Sound and breathing","Sonidos y respiración","Notice one sound near you and one sound farther away. Alternate your attention between them and your comfortable breathing.","Nota un sonido cercano y otro más lejano. Alterna tu atención entre ambos y tu respiración cómoda."),
("three_colors",45,"Find three colors","Encuentra tres colores","Look around and find three colors. Name them silently. Let this simple search settle your attention while you breathe naturally.","Mira a tu alrededor y encuentra tres colores. Nómbralos en silencio. Deja que esta búsqueda sencilla centre tu atención mientras respiras naturalmente."),
("five_small_details",45,"Notice small details","Observa pequeños detalles","Find a small detail you had not noticed before. Observe its shape or texture without needing to describe it aloud.","Encuentra un pequeño detalle que antes no habías notado. Observa su forma o textura sin necesidad de describirlo en voz alta."),
("present_moment",40,"Return to now","Vuelve al presente","Notice where you are, what supports your body, and one thing you can see. There is no need to change anything.","Observa dónde estás, qué sostiene tu cuerpo y una cosa que puedes ver. No necesitas cambiar nada."),
("slow_attention",45,"Move attention slowly","Mueve la atención despacio","Move your attention from your hands to your shoulders and then to your feet. Keep every part relaxed and breathe in your usual way.","Lleva tu atención de las manos a los hombros y después a los pies. Mantén el cuerpo relajado y respira como acostumbras."),
("face_check",40,"A gentle face check","Revisa suavemente tu rostro","Notice your eyes, cheeks, and jaw. If any area feels tense, allow it to soften only as much as feels comfortable.","Observa los ojos, las mejillas y la mandíbula. Si alguna zona está tensa, permite que se relaje solo hasta donde te resulte cómodo."),
("neck_comfort",40,"Comfort for your neck","Comodidad para el cuello","Keep your head in a comfortable position. Avoid stretching or forcing movement. Notice the support beneath you and breathe easily.","Mantén la cabeza en una posición cómoda. Evita estirar o forzar movimientos. Nota el apoyo que tienes y respira con comodidad."),
("soft_fingers",40,"Relax each finger","Relaja los dedos","Notice your fingers one by one. Let them rest naturally instead of holding them stiffly. Continue breathing without a set rhythm.","Observa los dedos uno por uno. Déjalos descansar de forma natural en lugar de mantenerlos rígidos. Continúa respirando sin un ritmo fijo."),
("comfortable_posture",45,"Find your posture","Encuentra tu postura","Make one small adjustment to feel more comfortable, if needed. Then stop adjusting and let your body rest in its chosen position.","Haz un pequeño ajuste para estar más cómodo, si lo necesitas. Después deja de cambiar de postura y descansa en la posición elegida."),
("release_the_brow",40,"Soften your brow","Suaviza el entrecejo","Imagine the space between your eyebrows becoming smooth. Let your eyes rest naturally and keep your breathing gentle.","Imagina que se alisa el espacio entre las cejas. Deja descansar los ojos de forma natural y mantén una respiración suave."),
("quiet_number",45,"A quiet number game","Un juego numérico tranquilo","Count backward from ten at your own pace. If you lose your place, choose another number and continue without pressure.","Cuenta hacia atrás desde diez a tu propio ritmo. Si pierdes la cuenta, elige otro número y continúa sin presión."),
("word_of_calm",40,"Choose a calming word","Elige una palabra tranquila","Choose a word such as easy, steady, or enough. Repeat it silently when useful, without matching it to a forced breathing pattern.","Elige una palabra como calma, suave o suficiente. Repítela en silencio cuando te ayude, sin imponerle un patrón a la respiración."),
("tiny_gratitude",45,"One small appreciation","Agradece algo pequeño","Think of one ordinary thing you appreciate today. It can be very small. Notice it briefly and return to your natural breathing.","Piensa en algo cotidiano que agradezcas hoy. Puede ser muy pequeño. Obsérvalo un momento y vuelve a tu respiración natural."),
("let_it_be",45,"Let this moment be","Deja que este momento exista","Allow this moment to be exactly as it is. You do not need to feel peaceful or happy. Simply give yourself a little room to breathe.","Permite que este momento sea tal como es. No tienes que sentir paz ni felicidad. Simplemente date un poco de espacio para respirar."),
("no_performance",40,"Nothing to perform","No tienes que demostrar nada","This is not a test. There is no score and no perfect breath. Let your body breathe by itself while you take a short pause.","Esto no es una prueba. No hay puntuación ni respiración perfecta. Deja que tu cuerpo respire por sí mismo mientras haces una pausa."),
("gentle_reset",45,"A gentle reset","Un reinicio suave","Imagine setting down a heavy bag after a walk. You do not need to carry every thought during these few seconds. Breathe comfortably.","Imagina que dejas en el suelo una bolsa pesada después de caminar. No tienes que cargar con todos los pensamientos durante estos segundos. Respira cómodamente."),
("fresh_start",45,"A fresh start","Un nuevo comienzo","Think of the next moment as a clean page. You do not need to plan the whole day. Give your attention to one comfortable breath at a time.","Piensa en el próximo momento como una página nueva. No necesitas planificar todo el día. Presta atención a una respiración cómoda cada vez."),
("inner_weather",45,"Notice your inner weather","Observa tu clima interior","Ask yourself whether this moment feels sunny, cloudy, or mixed. There is no wrong answer. Observe the feeling without forcing it to change.","Pregúntate si este momento se siente soleado, nublado o cambiante. No hay respuesta incorrecta. Observa la sensación sin forzar un cambio."),
("room_to_choose",45,"You have a choice","Puedes elegir","Choose where to place your attention: a sound, a color, or the feeling of your feet. Switch whenever you wish while breathing naturally.","Elige dónde poner tu atención: un sonido, un color o la sensación de tus pies. Cambia cuando quieras mientras respiras naturalmente."),
("gentle_rhythm",45,"Notice your own rhythm","Observa tu propio ritmo","There is no required speed. Notice the rhythm your body has chosen today and allow it to remain comfortable.","No existe una velocidad obligatoria. Observa el ritmo que tu cuerpo ha elegido hoy y permite que siga siendo cómodo."),
("easy_in_easy_out",45,"Easy in, easy out","Entra y sale suavemente","Notice the beginning and end of each breath. Do not extend either part. Simply let inhaling and exhaling happen naturally.","Observa el comienzo y el final de cada respiración. No prolongues ninguna parte. Deja que inhalar y exhalar sucedan naturalmente."),
("breath_without_numbers",45,"No counting needed","No necesitas contar","Forget the numbers for a moment. Notice the simple sensation of breathing. If your attention wanders, return gently without criticism.","Olvida los números por un momento. Nota la sencilla sensación de respirar. Si te distraes, vuelve suavemente sin criticarte."),
("light_as_air",45,"Light as air","Ligero como el aire","Imagine a feather resting on a table. There is no need to move it. Let the image remind you to release unnecessary effort.","Imagina una pluma descansando sobre una mesa. No necesitas moverla. Deja que la imagen te recuerde que puedes soltar esfuerzos innecesarios."),
("safe_pause",45,"A safe little pause","Una pequeña pausa segura","Look around and remind yourself of one ordinary thing that feels familiar. Stay aware of your surroundings and let your breath remain easy.","Mira a tu alrededor y recuerda algo cotidiano que te resulte familiar. Mantente consciente de tu entorno y respira cómodamente."),
("kind_to_today",45,"Be kind to today","Sé amable contigo hoy","Whatever today has brought, you can take these seconds without judging yourself. Allow one natural breath, followed by another.","Sea lo que sea que haya traído el día, puedes tomarte estos segundos sin juzgarte. Deja llegar una respiración natural y después otra."),
("little_by_little",45,"Little by little","Poco a poco","You do not need to feel different all at once. Give yourself this small pause and let each comfortable breath happen in its own time.","No necesitas sentirte diferente de inmediato. Regálate esta pequeña pausa y deja que cada respiración cómoda ocurra a su tiempo."),
("quiet_horizon",45,"Look toward the horizon","Mira hacia el horizonte","If possible, look toward a distant point without straining your eyes. Let your gaze rest and keep your breathing natural.","Si puedes, mira hacia un punto lejano sin forzar la vista. Deja descansar la mirada y mantén tu respiración natural."),
("still_water",45,"Still water","Agua tranquila","Imagine a pond at dawn before anyone arrives. Watch its calm surface in your mind and let your attention settle without controlling your breath.","Imagina un estanque al amanecer, antes de que llegue nadie. Observa mentalmente su superficie tranquila y deja reposar tu atención sin controlar la respiración."),
("soft_landing",45,"Land softly in this moment","Aterriza suavemente en el presente","Notice the surface beneath your body and the room around you. Let your attention settle as if arriving home after a long day.","Nota la superficie que sostiene tu cuerpo y la habitación que te rodea. Deja que tu atención se asiente como al llegar a casa después de un día largo."),
("small_space",45,"A little space for yourself","Un espacio para ti","For these few seconds, give yourself the same patience you would offer a friend. Breathe comfortably and let the moment unfold.","Durante estos segundos, date la misma paciencia que ofrecerías a un amigo. Respira cómodamente y deja que el momento transcurra."),
("finish_with_ease",45,"Finish with ease","Termina con tranquilidad","Notice one last comfortable breath. Look around, feel your feet, and prepare to return to your day at your own pace.","Nota una última respiración cómoda. Mira a tu alrededor, siente los pies y prepárate para volver a tu día a tu propio ritmo."),
]

def make_exercise(item):
    exercise_id, duration, title_en, title_es, instructions_en, instructions_es = item
    return {
        "id": exercise_id,
        "duration_seconds": duration,
        "type": "breathing_calm",
        "title": {"en": title_en, "es": title_es},
        "instructions": {"en": instructions_en, "es": instructions_es},
        "breathing_pattern": {
            "inhale_seconds": 3,
            "exhale_seconds": 4,
            "hold_seconds": 0,
        },
    }

# Los cuatro ejercicios originales se conservan.
ORIGINAL_EXERCISES = [
    {
        "id": "natural_breathing",
        "duration_seconds": 45,
        "type": "breathing",
        "title": {"en": "Natural breathing", "es": "Respiración natural"},
        "instructions": {
            "en": "Sit comfortably. Breathe naturally and gently. Do not hold your breath or force deep breaths. Stop if you feel dizzy or uncomfortable.",
            "es": "Siéntate cómodamente. Respira de forma natural y suave. No retengas el aire ni fuerces respiraciones profundas. Detente si sientes mareo o incomodidad.",
        },
    },
    {
        "id": "shoulder_release",
        "duration_seconds": 45,
        "type": "gentle_movement",
        "title": {"en": "Shoulder release", "es": "Relaja los hombros"},
        "instructions": {
            "en": "If comfortable, gently lift your shoulders, then let them drop and relax. Repeat slowly. You can skip the movement and simply rest.",
            "es": "Si te resulta cómodo, eleva suavemente los hombros y después déjalos bajar y relajarse. Repite despacio. Puedes omitir el movimiento y simplemente descansar.",
        },
    },
    {
        "id": "hand_wake_up",
        "duration_seconds": 40,
        "type": "gentle_movement",
        "title": {"en": "Wake up your hands", "es": "Activa las manos"},
        "instructions": {
            "en": "Slowly open and close your fingers, then relax your hands. Keep the movement easy and pain-free.",
            "es": "Abre y cierra lentamente los dedos y después relaja las manos. Haz movimientos cómodos y sin dolor.",
        },
    },
    {
        "id": "rest_the_eyes",
        "duration_seconds": 45,
        "type": "passive_rest",
        "title": {"en": "Rest your eyes", "es": "Descansa la vista"},
        "instructions": {
            "en": "Look away from the screen at a comfortable distance. Let your face and jaw relax and rest your eyes without straining.",
            "es": "Aparta la mirada de la pantalla y mira a una distancia cómoda. Relaja el rostro y la mandíbula y descansa la vista sin esfuerzo.",
        },
    },
]

DEFAULT_EXERCISES = ORIGINAL_EXERCISES + [
    make_exercise(item) for item in EXERCISE_CONTENT
]

# Validación básica de ejercicios personalizados.
def valid_exercise(item):
    if not isinstance(item, dict):
        return False
    if not isinstance(item.get("id"), str) or not item["id"].strip():
        return False
    if not isinstance(item.get("title"), dict):
        return False
    if not isinstance(item.get("instructions"), dict):
        return False
    for language in ("en", "es"):
        if not str(item["title"].get(language, "")).strip():
            return False
        if not str(item["instructions"].get(language, "")).strip():
            return False
    try:
        duration = int(item.get("duration_seconds", 45))
    except (TypeError, ValueError):
        return False
    return 10 <= duration <= 300

def merge_exercises(custom_exercises):
    """Conserva los 64 ejercicios base y admite extras del JSON sin duplicar IDs."""
    merged = {item["id"]: deepcopy(item) for item in DEFAULT_EXERCISES}
    if isinstance(custom_exercises, list):
        for item in custom_exercises:
            if not valid_exercise(item):
                continue
            merged[item["id"]] = deepcopy(item)
    return list(merged.values())

# CARGA Y VALIDACIÓN DEL JSON
def load_database():
    if not DATA_FILE.is_file():
        logger.warning("No se encontró %s; se usarán ejercicios predeterminados.", DATA_FILE)
        return [], {
            "easy_reset_exercises": deepcopy(DEFAULT_EXERCISES),
            "safety_notes": deepcopy(DEFAULT_SAFETY),
            "target_session_seconds": 300,
        }

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        config = {}
        if isinstance(data, list):
            questions = data
        elif isinstance(data, dict):
            config = dict(data.get("app_config") or {})
            if isinstance(data.get("questions"), list):
                questions = data["questions"]
            else:
                categories = data.get("categories", data)
                questions = []
                if isinstance(categories, dict):
                    for category, items in categories.items():
                        if category == "app_config" or not isinstance(items, list):
                            continue
                        for item in items:
                            if isinstance(item, dict):
                                question = dict(item)
                                question.setdefault("topic", category)
                                questions.append(question)
        else:
            questions = []

        valid_questions = []
        for question in questions:
            if not isinstance(question, dict):
                continue
            if not isinstance(question.get("en"), dict) or not isinstance(question.get("es"), dict):
                continue
            question = deepcopy(question)
            if not question["en"].get("prompt") or not question["es"].get("prompt"):
                continue
            valid_questions.append(question)

        exercises = merge_exercises(config.get("easy_reset_exercises"))
        safety_notes = config.get("safety_notes")
        if not isinstance(safety_notes, dict):
            safety_notes = deepcopy(DEFAULT_SAFETY)
        else:
            safety_notes = {
                "en": safety_notes.get("en") or DEFAULT_SAFETY["en"],
                "es": safety_notes.get("es") or DEFAULT_SAFETY["es"],
            }

        try:
            session_seconds = int(config.get("target_session_seconds", 300))
        except (TypeError, ValueError):
            session_seconds = 300
        if session_seconds <= 0:
            session_seconds = 300

        normalized_config = {
            "easy_reset_exercises": exercises,
            "safety_notes": safety_notes,
            "target_session_seconds": session_seconds,
        }

        logger.info(
            "JSON cargado: %s preguntas y %s ejercicios.",
            len(valid_questions), len(exercises)
        )
        return valid_questions, normalized_config

    except (OSError, json.JSONDecodeError):
        logger.exception("No se pudo leer el JSON.")
    except Exception:
        logger.exception("Error inesperado al cargar la base de datos.")

    return [], {
        "easy_reset_exercises": deepcopy(DEFAULT_EXERCISES),
        "safety_notes": deepcopy(DEFAULT_SAFETY),
        "target_session_seconds": 300,
    }

QUESTIONS, APP_CONFIG = load_database()
EXERCISES = APP_CONFIG["easy_reset_exercises"]
SAFETY_NOTES = APP_CONFIG["safety_notes"]

# MEZCLAR OPCIONES SIN PERDER LA RESPUESTA CORRECTA
def shuffle_localized_options(localized):
    localized = deepcopy(localized)
    options = localized.get("options")
    if not isinstance(options, list) or len(options) < 2:
        return localized

    correct_answer = localized.get("correct_answer")
    is_index = isinstance(correct_answer, int) and not isinstance(correct_answer, bool)
    correct_text = options[correct_answer] if is_index and 0 <= correct_answer < len(options) else None
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

# PÁGINA PRINCIPAL
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )

# ESTADO DE LA APLICACIÓN
@app.get("/api/status")
def status():
    return {
        "message": "API Activa",
        "database_loaded": len(QUESTIONS) > 0,
        "total_cards_loaded": len(QUESTIONS),
        "categories": sorted({
            question.get("topic", "General") for question in QUESTIONS
        }),
        "exercises_loaded": len(EXERCISES),
        "session_seconds": APP_CONFIG["target_session_seconds"],
        "data_file": DATA_FILE.name,
    }

# SESIÓN DE CINCO MINUTOS
@app.get("/api/session")
def create_session():
    questions = list(QUESTIONS)
    random.shuffle(questions)
    exercises = deepcopy(EXERCISES)
    random.shuffle(exercises)
    return {
        "questions": [
            copy_and_shuffle_options(question) for question in questions
        ],
        "exercises": exercises,
        "safety_notes": SAFETY_NOTES,
        "session_seconds": APP_CONFIG["target_session_seconds"],
    }

# API ANTERIOR: COMPATIBILIDAD CON EL HTML EXISTENTE
@app.post("/api/next-card")
async def next_card(request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = {}
    except Exception:
        body = {}

    index = body.get("index")
    if isinstance(index, int) and not isinstance(index, bool):
        if 0 <= index < len(QUESTIONS):
            return copy_and_shuffle_options(QUESTIONS[index])
        return {"message": "Completed", "finished": True}

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
            card = copy_and_shuffle_options(category_questions[category_index])
            next_indices = dict(indices)
            next_indices[category] = category_index + 1
            card["next_indices"] = next_indices
            return card

    return {"message": "Completed", "finished": True}

# COMPROBACIÓN BÁSICA
@app.get("/health")
def health():
    return {
        "status": "ok",
        "database_loaded": len(QUESTIONS) > 0,
    }
