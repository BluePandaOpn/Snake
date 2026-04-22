# Version 1.2.5 - Difficulty Levels Update
import json
import math
import os
import random
import re
import sys
import threading
import time
from datetime import datetime, timezone
from urllib import request as urllib_request

import pygame

# Intentar importar requests para una descarga más robusta, sino usar urllib
try:
    import requests
except ImportError:
    requests = None

# --- CONFIGURACIÓN DE RUTAS Y RECURSOS ---
def get_app_dir():
    """Devuelve la carpeta base persistente del juego para guardar datos y recursos."""
    if getattr(sys, "frozen", False):
        documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
        return ensure_directory(os.path.join(documents_dir, "GameSnake", "Game"))
    return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """Resuelve rutas de recursos tanto en desarrollo como en ejecutable empaquetado."""
    base_path = getattr(sys, "_MEIPASS", get_app_dir())
    return os.path.join(base_path, relative_path)

def ensure_directory(path):
    """Crea una carpeta si no existe."""
    os.makedirs(path, exist_ok=True)
    return path

def file_exists_and_has_data(path):
    """Comprueba que un archivo exista y no esté vacío."""
    return os.path.isfile(path) and os.path.getsize(path) > 0

# --- SISTEMA DE DESCARGA Y AUDIO ---
pygame.init()
AUDIO_AVAILABLE = True
try:
    pygame.mixer.init()
except pygame.error:
    AUDIO_AVAILABLE = False

APP_DIR = get_app_dir()
RES_DIR = ensure_directory(os.path.join(APP_DIR, "res"))
AUDIO_CACHE = {}

# URLs de los sonidos originales
BACKGROUND_MUSIC_URL = "https://raw.githubusercontent.com/BluePandaOpn/Snake/main/res/fondo.mp3"
DIRECTION_SOUND_URL = "https://raw.githubusercontent.com/BluePandaOpn/Snake/main/res/cambio_de_direcion.mp3"

AUDIO_SOURCES = {
    "fondo.mp3": BACKGROUND_MUSIC_URL,
    "cambio_de_direcion.mp3": DIRECTION_SOUND_URL,
}

# --- VARIABLES GLOBALES DE CONFIGURACIÓN ---
# Niveles: 10 (Fácil), 15 (Normal), 25 (Difícil), 40 (Infernal)
BASE_SPEED = 15
SOUND_ENABLED = True
GRAPHICS_HIGH = True 

def download_file(url, destination, timeout=5):
    """Descarga un archivo de forma segura."""
    ensure_directory(os.path.dirname(destination))
    try:
        if requests is not None:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            with open(destination, "wb") as f:
                f.write(response.content)
            return True
        with urllib_request.urlopen(url, timeout=timeout) as response, open(destination, "wb") as f:
            f.write(response.read())
        return True
    except Exception:
        return False

def ensure_audio_file(filename):
    """Verifica si el audio existe localmente o lo descarga."""
    cached_path = os.path.join(RES_DIR, filename)
    if file_exists_and_has_data(cached_path):
        return cached_path
    url = AUDIO_SOURCES.get(filename)
    if url and download_file(url, cached_path):
        return cached_path
    return None

def get_sound(sound_name):
    """Carga un sonido en la caché y lo devuelve."""
    if not AUDIO_AVAILABLE or not SOUND_ENABLED: return None
    if sound_name in AUDIO_CACHE: return AUDIO_CACHE[sound_name]
    
    path = ensure_audio_file(sound_name)
    if not path:
        AUDIO_CACHE[sound_name] = None
        return None
    try:
        AUDIO_CACHE[sound_name] = pygame.mixer.Sound(path)
    except:
        AUDIO_CACHE[sound_name] = None
    return AUDIO_CACHE[sound_name]

def play_sound(sound_name):
    """Reproduce un efecto de sonido."""
    if not SOUND_ENABLED: return
    sound = get_sound(sound_name)
    if sound:
        try: sound.play()
        except: pass

def ensure_background_music():
    """Carga y reproduce la música de fondo en bucle."""
    if not AUDIO_AVAILABLE: return False
    if not SOUND_ENABLED:
        pygame.mixer.music.stop()
        return False
    path = ensure_audio_file("fondo.mp3")
    if not path: return False
    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)
        return True
    except: return False

def set_game_icon():
    """Carga el icono de la ventana del juego."""
    icon_path = get_resource_path("ico.ico")
    if not os.path.isfile(icon_path):
        return
    try:
        pygame.display.set_icon(pygame.image.load(icon_path))
    except pygame.error:
        pass

def preload_audio_async():
    """Pre-descarga los sonidos en un hilo separado para no bloquear el inicio."""
    threading.Thread(target=lambda: (ensure_audio_file("fondo.mp3"), ensure_audio_file("cambio_de_direcion.mp3")), daemon=True).start()

# --- CONFIGURACIÓN DE COLORES Y UI ---
COLOR_BG = (40, 40, 45)
COLOR_SNAKE = (46, 204, 113)
COLOR_SNAKE_HEAD = (39, 174, 96)
COLOR_FOOD = (231, 76, 60)
COLOR_TEXT = (236, 240, 241)
COLOR_UI_BAR = (30, 30, 35)
COLOR_GOLD = (241, 196, 15)
COLOR_BUTTON = (52, 73, 94)
COLOR_BUTTON_HOVER = (93, 109, 126)
COLOR_POWERUP = (155, 89, 182)
COLOR_OBSTACLE = (127, 140, 141)

WIDTH = 1200
HEIGHT = 760
TOP_BAR_HEIGHT = 50
SNAKE_BLOCK = 20
FOOD_SIZE = 14
FPS = 60
COMBO_WINDOW_MS = 3000
POWERUP_DURATION_MS = 5000
POWERUP_SPAWN_INTERVAL_MS = 9000
POWERUP_LIFETIME_MS = 4500
MOVE_SMOOTHING = 0.28
PAUSE_KEYS = (pygame.K_p, pygame.K_ESCAPE)
TIME_ATTACK_START_MS = 60000
TIME_ATTACK_BONUS_MS = 4000

dis = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Snake Pro - Ultimate Edition')
set_game_icon()
clock = pygame.time.Clock()

font_ui = pygame.font.SysFont("arial", 22, bold=True)
font_title = pygame.font.SysFont("arial", 80, bold=True)
font_gameover = pygame.font.SysFont("arial", 60, bold=True)
font_btn = pygame.font.SysFont("arial", 30, bold=True)
font_label = pygame.font.SysFont("arial", 24, bold=True)
font_shop_name = pygame.font.SysFont("arial", 22, bold=True)
font_shop_meta = pygame.font.SysFont("arial", 18, bold=True)
font_mission_card = pygame.font.SysFont("arial", 26, bold=True)
font_mission_meta = pygame.font.SysFont("arial", 20, bold=True)

DATA_FILE = os.path.join(APP_DIR, "snake_data.json")

SNAKE_SKINS = [
    {
        "id": "classic",
        "name": "CLASICA",
        "body": (46, 204, 113),
        "head": (39, 174, 96),
        "cups": 0,
    },
    {
        "id": "ocean",
        "name": "OCEANO",
        "body": (52, 152, 219),
        "head": (41, 128, 185),
        "cups": 15,
    },
    {
        "id": "sun",
        "name": "SOL",
        "body": (241, 196, 15),
        "head": (243, 156, 18),
        "cups": 30,
    },
    {
        "id": "rose",
        "name": "ROSA",
        "body": (232, 67, 147),
        "head": (182, 52, 113),
        "cups": 50,
    },
    {
        "id": "lava",
        "name": "LAVA",
        "body": (230, 126, 34),
        "head": (211, 84, 0),
        "cups": 70,
    },
    {
        "id": "ice",
        "name": "HIELO",
        "body": (129, 236, 236),
        "head": (0, 184, 148),
        "cups": 90,
    },
    {
        "id": "violet",
        "name": "VIOLETA",
        "body": (162, 155, 254),
        "head": (108, 92, 231),
        "cups": 115,
    },
    {
        "id": "shadow",
        "name": "SOMBRA",
        "body": (99, 110, 114),
        "head": (45, 52, 54),
        "cups": 145,
    },
    {
        "id": "mint",
        "name": "MENTA",
        "body": (85, 239, 196),
        "head": (0, 184, 148),
        "cups": 180,
    },
    {
        "id": "ruby",
        "name": "RUBI",
        "body": (214, 48, 49),
        "head": (179, 0, 0),
        "cups": 220,
    },
    {
        "id": "golden",
        "name": "DORADA",
        "body": (255, 234, 167),
        "head": (253, 203, 110),
        "cups": 260,
    },
    {
        "id": "neon",
        "name": "NEON",
        "body": (0, 255, 170),
        "head": (0, 214, 143),
        "cups": 320,
    },
    {
        "id": "galaxy",
        "name": "GALAXIA",
        "body": (116, 75, 162),
        "head": (52, 31, 151),
        "cups": 400,
    },
]
DEFAULT_SKIN_ID = SNAKE_SKINS[0]["id"]
GAME_MODES = [
    {"id": "classic", "name": "CLASICO"},
    {"id": "zen", "name": "ZEN"},
    {"id": "time_attack", "name": "CONTRARRELOJ"},
]
DEFAULT_MODE_ID = GAME_MODES[0]["id"]
MISSION_POOL = [
    {"id": "eat_30", "text": "Come 30 frutas", "target": 30, "reward": 15, "kind": "fruit_total"},
    {"id": "eat_50", "text": "Come 50 frutas", "target": 50, "reward": 25, "kind": "fruit_total"},
    {"id": "infernal_20", "text": "Llega a 20 puntos en Infernal", "target": 20, "reward": 30, "kind": "infernal_score"},
    {"id": "zen_35", "text": "Llega a 35 puntos en Zen", "target": 35, "reward": 30, "kind": "zen_score"},
    {"id": "time_15", "text": "Come 15 frutas en Contrarreloj", "target": 15, "reward": 25, "kind": "time_attack_fruits"},
]

def get_mode_by_id(mode_id):
    for mode in GAME_MODES:
        if mode["id"] == mode_id:
            return mode
    return GAME_MODES[0]

def get_today_key():
    return datetime.now().strftime("%Y-%m-%d")

def get_mission_by_id(mission_id):
    for mission in MISSION_POOL:
        if mission["id"] == mission_id:
            return mission
    return None

def build_daily_missions(date_key):
    rng = random.Random(date_key)
    return [mission["id"] for mission in rng.sample(MISSION_POOL, 2)]

def normalize_daily_data(data):
    today_key = get_today_key()
    mission_ids = data.get("daily_missions", [])
    if data.get("daily_date") != today_key or len(mission_ids) != 2:
        mission_ids = build_daily_missions(today_key)
        data["daily_date"] = today_key
        data["daily_missions"] = mission_ids
        data["daily_progress"] = {}
        data["daily_claimed"] = []
    data["daily_progress"] = dict(data.get("daily_progress", {}))
    data["daily_claimed"] = [mid for mid in data.get("daily_claimed", []) if get_mission_by_id(mid)]
    return data

def get_daily_mission_rows():
    rows = []
    for mission_id in daily_missions:
        mission = get_mission_by_id(mission_id)
        if mission is None:
            continue
        progress = min(daily_progress.get(mission_id, 0), mission["target"])
        claimed = mission_id in daily_claimed
        status = "COMPLETADA" if claimed else f"{progress}/{mission['target']}"
        rows.append(f"{mission['text']} - {status} (+{mission['reward']} copas)")
    return rows

def get_daily_mission_cards():
    cards = []
    for mission_id in daily_missions:
        mission = get_mission_by_id(mission_id)
        if mission is None:
            continue
        progress = min(daily_progress.get(mission_id, 0), mission["target"])
        claimed = mission_id in daily_claimed
        cards.append(
            {
                "title": mission["text"],
                "progress": progress,
                "target": mission["target"],
                "reward": mission["reward"],
                "claimed": claimed,
            }
        )
    return cards

def update_daily_missions(game_mode, fruits_collected, score_value):
    global cups
    changed = False
    for mission_id in daily_missions:
        mission = get_mission_by_id(mission_id)
        if mission is None:
            continue
        progress_value = daily_progress.get(mission_id, 0)
        if mission["kind"] == "fruit_total":
            progress_value = max(progress_value, fruits_collected)
        elif mission["kind"] == "infernal_score" and BASE_SPEED == 40:
            progress_value = max(progress_value, score_value)
        elif mission["kind"] == "zen_score" and game_mode == "zen":
            progress_value = max(progress_value, score_value)
        elif mission["kind"] == "time_attack_fruits" and game_mode == "time_attack":
            progress_value = max(progress_value, fruits_collected)
        daily_progress[mission_id] = progress_value
        if progress_value >= mission["target"] and mission_id not in daily_claimed:
            daily_claimed.append(mission_id)
            cups += mission["reward"]
            changed = True
    if changed:
        save_data()

def get_skin_by_id(skin_id):
    for skin in SNAKE_SKINS:
        if skin["id"] == skin_id:
            return skin
    return SNAKE_SKINS[0]

def load_data():
    data = {
        "high_score": 0,
        "cups": 0,
        "selected_skin": DEFAULT_SKIN_ID,
        "current_mode": DEFAULT_MODE_ID,
        "sound_enabled": SOUND_ENABLED,
        "graphics_high": GRAPHICS_HIGH,
        "base_speed": BASE_SPEED,
        "daily_date": get_today_key(),
        "daily_missions": build_daily_missions(get_today_key()),
        "daily_progress": {},
        "daily_claimed": [],
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                data["high_score"] = int(saved.get("high_score", 0))
                data["cups"] = int(saved.get("cups", data["high_score"]))
                data["selected_skin"] = saved.get("selected_skin", DEFAULT_SKIN_ID)
                data["current_mode"] = saved.get("current_mode", DEFAULT_MODE_ID)
                data["sound_enabled"] = bool(saved.get("sound_enabled", SOUND_ENABLED))
                data["graphics_high"] = bool(saved.get("graphics_high", GRAPHICS_HIGH))
                data["base_speed"] = int(saved.get("base_speed", BASE_SPEED))
                data["daily_date"] = saved.get("daily_date", data["daily_date"])
                data["daily_missions"] = saved.get("daily_missions", data["daily_missions"])
                data["daily_progress"] = saved.get("daily_progress", {})
                data["daily_claimed"] = saved.get("daily_claimed", [])
        except:
            pass
    if data["selected_skin"] not in {skin["id"] for skin in SNAKE_SKINS}:
        data["selected_skin"] = DEFAULT_SKIN_ID
    if data["current_mode"] not in {mode["id"] for mode in GAME_MODES}:
        data["current_mode"] = DEFAULT_MODE_ID
    if data["base_speed"] not in {10, 15, 25, 40}:
        data["base_speed"] = BASE_SPEED
    return normalize_daily_data(data)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(
            {
                "high_score": high_score,
                "cups": cups,
                "selected_skin": selected_skin_id,
                "current_mode": current_mode_id,
                "sound_enabled": SOUND_ENABLED,
                "graphics_high": GRAPHICS_HIGH,
                "base_speed": BASE_SPEED,
                "daily_date": daily_date,
                "daily_missions": daily_missions,
                "daily_progress": daily_progress,
                "daily_claimed": daily_claimed,
            },
            f,
        )

game_data = load_data()
high_score = game_data["high_score"]
cups = game_data["cups"]
selected_skin_id = game_data["selected_skin"]
current_mode_id = game_data["current_mode"]
SOUND_ENABLED = game_data["sound_enabled"]
GRAPHICS_HIGH = game_data["graphics_high"]
BASE_SPEED = game_data["base_speed"]
daily_date = game_data["daily_date"]
daily_missions = game_data["daily_missions"]
daily_progress = game_data["daily_progress"]
daily_claimed = game_data["daily_claimed"]

def draw_ui(score):
    pygame.draw.rect(dis, COLOR_UI_BAR, [0, 0, WIDTH, TOP_BAR_HEIGHT])
    active_skin = get_skin_by_id(selected_skin_id)
    pygame.draw.rect(dis, active_skin["body"], [20, 15, 15, 15])
    dis.blit(font_ui.render(f": {score}", True, COLOR_TEXT), [40, 12])
    pygame.draw.rect(dis, COLOR_GOLD, [130, 15, 15, 10]) 
    pygame.draw.rect(dis, COLOR_GOLD, [135, 25, 5, 10])  
    pygame.draw.rect(dis, COLOR_GOLD, [132, 32, 11, 3])  
    dis.blit(font_ui.render(f": {high_score}", True, COLOR_GOLD), [155, 12])
    dis.blit(font_ui.render(f"COPAS: {cups}", True, COLOR_GOLD), [WIDTH - 160, 12])

def draw_game_status(combo_count, active_effects):
    x_pos = 320
    if combo_count > 1:
        combo_text = font_ui.render(f"COMBO x{combo_count}", True, COLOR_GOLD)
        dis.blit(combo_text, [x_pos, 12])
        x_pos += combo_text.get_width() + 25
    for effect_name in active_effects:
        effect_text = font_ui.render(effect_name, True, COLOR_POWERUP)
        dis.blit(effect_text, [x_pos, 12])
        x_pos += effect_text.get_width() + 20

def draw_pause_overlay():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    dis.blit(overlay, (0, 0))
    pause_title = font_gameover.render("PAUSA", True, COLOR_TEXT)
    pause_hint = font_label.render("Pulsa P o ESC para continuar", True, COLOR_GOLD)
    dis.blit(pause_title, pause_title.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 20)))
    dis.blit(pause_hint, pause_hint.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 40)))

def draw_particles(particles):
    for particle in particles:
        radius = max(2, int(particle["size"]))
        pygame.draw.rect(
            dis,
            particle["color"],
            (int(particle["x"]), int(particle["y"]), radius, radius),
        )

def our_snake(snake_block, snake_segments):
    """Dibuja la serpiente como CUADRADOS PERFECTOS."""
    active_skin = get_skin_by_id(selected_skin_id)
    for i, x in enumerate(snake_segments):
        color = active_skin["head"] if i == len(snake_segments) - 1 else active_skin["body"]
        pygame.draw.rect(dis, color, [x[0], x[1], snake_block, snake_block])

def get_smoothed_snake(snake_list, prev_snake_list, progress):
    smoothed = []
    prev_length = len(prev_snake_list)
    for index, current in enumerate(snake_list):
        previous = prev_snake_list[index] if index < prev_length else current
        smoothed.append(
            [
                previous[0] + (current[0] - previous[0]) * progress,
                previous[1] + (current[1] - previous[1]) * progress,
            ]
        )
    return smoothed

def create_food_particles(x, y):
    particles = []
    center_x = x + SNAKE_BLOCK / 2
    center_y = y + SNAKE_BLOCK / 2
    for _ in range(14):
        particles.append(
            {
                "x": center_x,
                "y": center_y,
                "vx": random.uniform(-3.4, 3.4),
                "vy": random.uniform(-3.6, 2.2),
                "life": random.randint(14, 24),
                "size": random.randint(3, 6),
                "color": COLOR_FOOD,
            }
        )
    return particles

def update_particles(particles):
    alive_particles = []
    for particle in particles:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["vy"] += 0.12
        particle["life"] -= 1
        particle["size"] *= 0.94
        if particle["life"] > 0 and particle["size"] >= 1.2:
            alive_particles.append(particle)
    return alive_particles

def get_random_grid_position():
    return [
        int(round(random.randrange(SNAKE_BLOCK, WIDTH - SNAKE_BLOCK) / 20.0) * 20.0),
        int(round(random.randrange(TOP_BAR_HEIGHT + SNAKE_BLOCK, HEIGHT - SNAKE_BLOCK) / 20.0) * 20.0),
    ]

def is_position_blocked(position, snake_list, obstacle_rects, extra_positions=None):
    px, py = position
    if any(part[0] == px and part[1] == py for part in snake_list):
        return True
    if extra_positions:
        if any(item[0] == px and item[1] == py for item in extra_positions):
            return True
    point_rect = pygame.Rect(px, py, SNAKE_BLOCK, SNAKE_BLOCK)
    return any(rect.colliderect(point_rect) for rect in obstacle_rects)

def spawn_item(snake_list, obstacle_rects, extra_positions=None):
    for _ in range(200):
        position = get_random_grid_position()
        if not is_position_blocked(position, snake_list, obstacle_rects, extra_positions):
            return position
    return get_random_grid_position()

def get_obstacle_rects():
    if BASE_SPEED < 25:
        return []
    size = SNAKE_BLOCK
    center_x = WIDTH // 2
    center_y = (HEIGHT + TOP_BAR_HEIGHT) // 2
    if BASE_SPEED >= 40:
        patterns = [
            [(-4, 0), (-3, 0), (-2, 0), (2, 0), (3, 0), (4, 0), (0, -3), (0, -2), (0, 2), (0, 3)],
            [(-3, -2), (-2, -2), (2, -2), (3, -2), (-3, 2), (-2, 2), (2, 2), (3, 2), (0, -1), (0, 1)],
            [(-2, -3), (-2, -2), (-2, 2), (-2, 3), (2, -3), (2, -2), (2, 2), (2, 3), (-1, 0), (1, 0)],
        ]
    else:
        patterns = [
            [(-3, 0), (-2, 0), (2, 0), (3, 0)],
            [(0, -2), (0, -1), (0, 1), (0, 2)],
            [(-2, -1), (-1, -1), (1, 1), (2, 1)],
        ]
    pattern = random.choice(patterns)
    return [
        pygame.Rect(center_x + ox * size, center_y + oy * size, size, size)
        for ox, oy in pattern
    ]

def get_safe_obstacle_rects(snake_list, blocked_positions=None):
    blocked_positions = blocked_positions or []
    blocked_rects = [pygame.Rect(pos[0], pos[1], SNAKE_BLOCK, SNAKE_BLOCK) for pos in snake_list + blocked_positions]
    for _ in range(40):
        obstacle_rects = get_obstacle_rects()
        if not any(any(rect.colliderect(blocked) for blocked in blocked_rects) for rect in obstacle_rects):
            return obstacle_rects
    return []

def get_powerup_name(powerup_type):
    names = {
        "rayo": "RAYO",
        "tortuga": "TORTUGA",
        "iman": "IMAN",
        "fantasma": "FANTASMA",
    }
    return names.get(powerup_type, "")

def get_safe_food_position(snake_list, obstacle_rects, extra_positions=None):
    blocked_snake = {tuple(part) for part in snake_list}
    blocked_extra = {tuple(item) for item in (extra_positions or [])}
    position = spawn_item(snake_list, obstacle_rects, extra_positions)
    while tuple(position) in blocked_snake or tuple(position) in blocked_extra:
        position = spawn_item(snake_list, obstacle_rects, extra_positions)
    return position

def loading_animation():
    start_time = time.time()
    t = 0
    while time.time() - start_time < 1.5:
        dis.fill(COLOR_BG)
        load_txt = font_btn.render("CARGANDO RECURSOS...", True, COLOR_TEXT)
        dis.blit(load_txt, load_txt.get_rect(center=(WIDTH/2, HEIGHT/2 + 80)))
        for i in range(4):
            offset_y = math.sin(t + (i * 0.5)) * 10
            x_pos = (WIDTH / 2 - 44) + (i * 22)
            y_pos = (HEIGHT / 2 - 10) + offset_y
            color = COLOR_SNAKE_HEAD if i == 3 else COLOR_SNAKE
            pygame.draw.rect(dis, color, [x_pos, y_pos, 20, 20])
        t += 0.1
        pygame.display.update()
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

def draw_button(text, x, y, w, h, inactive_color, active_color, action=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    hover = x + w > mouse[0] > x and y + h > mouse[1] > y
    pygame.draw.rect(dis, active_color if hover else inactive_color, (x, y, w, h))
    if hover and click[0] == 1 and action is not None:
        time.sleep(0.15)
        return action()
    text_surf = font_btn.render(text, True, COLOR_TEXT)
    dis.blit(text_surf, text_surf.get_rect(center=(x + w/2, y + h/2)))

def options_menu():
    global BASE_SPEED, SOUND_ENABLED, GRAPHICS_HIGH, current_mode_id
    running = True
    while running:
        dis.fill(COLOR_BG)
        title = font_title.render("OPCIONES", True, COLOR_TEXT)
        dis.blit(title, title.get_rect(center=(WIDTH/2, 120)))
        
        # --- SECCIÓN GRÁFICOS ---
        lbl_gfx = font_label.render("GRÁFICOS", True, COLOR_GOLD)
        dis.blit(lbl_gfx, (WIDTH/2 - 300, 230))
        txt_gfx = "NORMAL" if GRAPHICS_HIGH else "SIMPLE"
        if draw_button(txt_gfx, WIDTH/2, 220, 250, 45, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "TOGGLE_GFX") == "TOGGLE_GFX":
            GRAPHICS_HIGH = not GRAPHICS_HIGH

        # --- SECCIÓN SONIDO ---
        lbl_snd = font_label.render("SONIDO", True, COLOR_GOLD)
        dis.blit(lbl_snd, (WIDTH/2 - 300, 300))
        txt_snd = "ACTIVADO" if SOUND_ENABLED else "MUTED"
        if draw_button(txt_snd, WIDTH/2, 290, 250, 45, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "TOGGLE_SND") == "TOGGLE_SND":
            SOUND_ENABLED = not SOUND_ENABLED
            if not SOUND_ENABLED:
                pygame.mixer.music.stop()
            else:
                ensure_background_music()

        # --- SECCIÓN DIFICULTAD ---
        # Niveles: Fácil (10), Normal (15), Difícil (25), Infernal (40)
        lbl_diff = font_label.render("DIFICULTAD", True, COLOR_GOLD)
        dis.blit(lbl_diff, (WIDTH/2 - 300, 370))
        
        if BASE_SPEED == 10: txt_diff = "FÁCIL"
        elif BASE_SPEED == 15: txt_diff = "NORMAL"
        elif BASE_SPEED == 25: txt_diff = "DIFÍCIL"
        else: txt_diff = "INFERNAL"
            
        if draw_button(txt_diff, WIDTH/2, 360, 250, 45, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "TOGGLE_DIFF") == "TOGGLE_DIFF":
            if BASE_SPEED == 10: BASE_SPEED = 15
            elif BASE_SPEED == 15: BASE_SPEED = 25
            elif BASE_SPEED == 25: BASE_SPEED = 40
            else: BASE_SPEED = 10

        lbl_mode = font_label.render("MODO", True, COLOR_GOLD)
        dis.blit(lbl_mode, (WIDTH/2 - 300, 440))
        txt_mode = get_mode_by_id(current_mode_id)["name"]
        if draw_button(txt_mode, WIDTH/2, 430, 250, 45, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "TOGGLE_MODE") == "TOGGLE_MODE":
            mode_ids = [mode["id"] for mode in GAME_MODES]
            current_index = mode_ids.index(current_mode_id)
            current_mode_id = mode_ids[(current_index + 1) % len(mode_ids)]
            save_data()

        # BOTÓN VOLVER
        if draw_button("VOLVER AL MENÚ", WIDTH/2 - 150, 610, 300, 60, COLOR_UI_BAR, COLOR_BUTTON_HOVER, lambda: "BACK") == "BACK":
            running = False

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        clock.tick(FPS)

def shop_menu():
    global selected_skin_id
    running = True
    while running:
        dis.fill(COLOR_BG)
        title = font_title.render("TIENDA", True, COLOR_TEXT)
        dis.blit(title, title.get_rect(center=(WIDTH/2, 110)))

        cups_text = font_label.render(f"COPAS DISPONIBLES: {cups}", True, COLOR_GOLD)
        dis.blit(cups_text, cups_text.get_rect(center=(WIDTH/2, 180)))

        start_y = 220
        card_width = 352
        card_height = 92
        card_gap_x = 12
        card_gap_y = 14
        left_x = WIDTH / 2 - ((card_width * 3) + (card_gap_x * 2)) / 2
        for index, skin in enumerate(SNAKE_SKINS):
            column = index % 3
            row = index // 3
            card_x = left_x + (column * (card_width + card_gap_x))
            card_y = start_y + (row * (card_height + card_gap_y))
            unlocked = cups >= skin["cups"]
            is_selected = selected_skin_id == skin["id"]

            pygame.draw.rect(dis, COLOR_UI_BAR, (card_x, card_y, card_width, card_height))
            pygame.draw.rect(dis, COLOR_BUTTON, (card_x + 1, card_y + 1, card_width - 2, card_height - 2), 2)
            pygame.draw.rect(dis, skin["body"], (card_x + 18, card_y + 21, 34, 34))
            pygame.draw.rect(dis, skin["head"], (card_x + 58, card_y + 21, 34, 34))
            pygame.draw.rect(dis, COLOR_BG, (card_x + 228, card_y + 14, 108, 38))

            name_text = font_shop_name.render(skin["name"], True, COLOR_TEXT)
            req_label = "LISTA" if unlocked else f"{skin['cups']} COPAS"
            req_color = COLOR_GOLD if unlocked else COLOR_TEXT
            req_text = font_shop_meta.render(req_label, True, req_color)
            info_text = font_shop_meta.render("DESBLOQUEO", True, COLOR_GOLD)
            dis.blit(name_text, (card_x + 110, card_y + 14))
            dis.blit(info_text, (card_x + 110, card_y + 48))
            dis.blit(req_text, (card_x + 110, card_y + 68))

            if is_selected:
                button_text = "EQUIPADA"
                button_color = COLOR_SNAKE_HEAD
                button_hover = COLOR_SNAKE
                action = None
            elif unlocked:
                button_text = "EQUIPAR"
                button_color = COLOR_BUTTON
                button_hover = COLOR_BUTTON_HOVER
                action = lambda skin_id=skin["id"]: skin_id
            else:
                button_text = "BLOQUEADA"
                button_color = COLOR_BG
                button_hover = COLOR_BG
                action = None

            result = draw_button(
                button_text,
                int(card_x + 226),
                int(card_y + 18),
                102,
                32,
                button_color,
                button_hover,
                action,
            )
            if result in {skin_item["id"] for skin_item in SNAKE_SKINS}:
                selected_skin_id = result
                save_data()

        if draw_button("VOLVER AL MENU", WIDTH/2 - 150, 690, 300, 42, COLOR_UI_BAR, COLOR_BUTTON_HOVER, lambda: "BACK") == "BACK":
            running = False

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        clock.tick(FPS)

def missions_menu():
    running = True
    while running:
        dis.fill(COLOR_BG)
        title = font_title.render("MISIONES", True, COLOR_TEXT)
        dis.blit(title, title.get_rect(center=(WIDTH / 2, 110)))
        subtitle = font_label.render("MISIONES DIARIAS DISPONIBLES", True, COLOR_GOLD)
        dis.blit(subtitle, subtitle.get_rect(center=(WIDTH / 2, 170)))

        cards = get_daily_mission_cards()
        card_width = 450
        card_height = 180
        gap_x = 40
        start_x = WIDTH / 2 - ((card_width * max(1, len(cards))) + (gap_x * max(0, len(cards) - 1))) / 2

        for index, card in enumerate(cards):
            card_x = start_x + index * (card_width + gap_x)
            card_y = 250
            progress_ratio = 0 if card["target"] == 0 else min(1.0, card["progress"] / card["target"])

            pygame.draw.rect(dis, COLOR_UI_BAR, (card_x, card_y, card_width, card_height), border_radius=10)
            pygame.draw.rect(dis, COLOR_BUTTON, (card_x + 2, card_y + 2, card_width - 4, card_height - 4), 2, border_radius=10)

            title_surface = font_mission_card.render(card["title"], True, COLOR_TEXT)
            dis.blit(title_surface, (card_x + 22, card_y + 24))

            reward_surface = font_mission_meta.render(f"RECOMPENSA: {card['reward']} COPAS", True, COLOR_GOLD)
            dis.blit(reward_surface, (card_x + 22, card_y + 74))

            progress_label = "COMPLETADA" if card["claimed"] else f"PROGRESO: {card['progress']}/{card['target']}"
            progress_color = COLOR_SNAKE if card["claimed"] else COLOR_TEXT
            progress_surface = font_mission_meta.render(progress_label, True, progress_color)
            dis.blit(progress_surface, (card_x + 22, card_y + 106))

            pygame.draw.rect(dis, COLOR_BG, (card_x + 22, card_y + 138, card_width - 44, 18), border_radius=9)
            pygame.draw.rect(dis, COLOR_GOLD if card["claimed"] else COLOR_SNAKE, (card_x + 22, card_y + 138, int((card_width - 44) * progress_ratio), 18), border_radius=9)

        if draw_button("VOLVER AL MENU", WIDTH / 2 - 150, 640, 300, 50, COLOR_UI_BAR, COLOR_BUTTON_HOVER, lambda: "BACK") == "BACK":
            running = False

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        clock.tick(FPS)

def main_menu():
    ensure_background_music()
    while True:
        dis.fill(COLOR_BG)
        title = font_title.render("SNAKE PRO", True, COLOR_SNAKE)
        dis.blit(title, title.get_rect(center=(WIDTH/2, 180)))
        mode_text = font_label.render(f"MODO: {get_mode_by_id(current_mode_id)['name']}", True, COLOR_GOLD)
        dis.blit(mode_text, mode_text.get_rect(center=(WIDTH/2, 240)))

        mission_button = draw_button("M", 28, HEIGHT / 2 - 40, 64, 64, COLOR_UI_BAR, COLOR_BUTTON_HOVER, lambda: "MISSIONS")
        mission_hint = font_shop_meta.render("MISIONES", True, COLOR_TEXT)
        dis.blit(mission_hint, (22, HEIGHT / 2 + 36))
        if mission_button == "MISSIONS":
            missions_menu()
        
        if draw_button("JUGAR", WIDTH/2 - 100, 320, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "PLAY") == "PLAY":
            loading_animation()
            gameLoop()
        if draw_button("OPCIONES", WIDTH/2 - 100, 400, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "OPT") == "OPT":
            options_menu()
        if draw_button("TIENDA", WIDTH/2 - 100, 480, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "SHOP") == "SHOP":
            shop_menu()
        if draw_button("SALIR", WIDTH/2 - 100, 560, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "EXIT") == "EXIT":
            pygame.quit(); sys.exit()

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        clock.tick(FPS)

def gameLoop():
    global high_score, cups, daily_progress, daily_claimed
    game_over = False
    game_close = False
    cups_awarded = False
    paused = False

    x1, y1 = (WIDTH // 2 // 20) * 20, (HEIGHT // 2 // 20) * 20
    dx, dy = 0, 0
    pending_direction = None
    snake_List = [[x1, y1]]
    prev_snake_list = [[x1, y1]]
    Length_of_snake = 1
    base_score = 0
    combo_count = 0
    last_food_time = 0
    score_multiplier = 1
    active_powerups = {}
    powerup = None
    start_time = pygame.time.get_ticks()
    next_powerup_spawn = start_time + POWERUP_SPAWN_INTERVAL_MS
    obstacle_rects = get_safe_obstacle_rects(snake_List, [])
    particles = []
    last_move_time = start_time
    fruits_collected = 0
    time_attack_end = start_time + TIME_ATTACK_START_MS if current_mode_id == "time_attack" else None

    foodx, foody = get_safe_food_position(snake_List, obstacle_rects)

    while not game_over:
        now = pygame.time.get_ticks()
        particles = update_particles(particles)
        active_effect_labels = []
        remaining_time_ms = None
        expired_powerups = [name for name, end_time in active_powerups.items() if now >= end_time]
        for powerup_name in expired_powerups:
            del active_powerups[powerup_name]

        if current_mode_id == "zen":
            active_effect_labels.append("ZEN")
        elif current_mode_id == "time_attack":
            remaining_time_ms = max(0, time_attack_end - now)
            active_effect_labels.append(f"TIEMPO {math.ceil(remaining_time_ms / 1000)}s")
            if remaining_time_ms <= 0:
                game_close = True

        if 'rayo' in active_powerups:
            score_multiplier = 2
            active_effect_labels.append('RAYO x2')
        else:
            score_multiplier = 1
        if 'tortuga' in active_powerups:
            active_effect_labels.append('TORTUGA')
        if 'iman' in active_powerups:
            active_effect_labels.append('IMAN')
        if 'fantasma' in active_powerups:
            active_effect_labels.append('FANTASMA')
        if combo_count > 1 and now - last_food_time > COMBO_WINDOW_MS:
            combo_count = 0

        if powerup and now - powerup['spawn_time'] >= POWERUP_LIFETIME_MS:
            powerup = None
        if powerup is None and now >= next_powerup_spawn:
            powerup_position = spawn_item(snake_List, obstacle_rects, [[foodx, foody]])
            powerup = {
                'type': random.choice(['rayo', 'tortuga', 'iman', 'fantasma']),
                'pos': powerup_position,
                'spawn_time': now,
            }
            next_powerup_spawn = now + POWERUP_SPAWN_INTERVAL_MS

        while game_close:
            if not cups_awarded:
                update_daily_missions(current_mode_id, fruits_collected, base_score * score_multiplier)
                cups += base_score
                cups_awarded = True
                save_data()
            dis.fill(COLOR_BG)
            msg = font_gameover.render('FIN DEL JUEGO', True, COLOR_FOOD)
            dis.blit(msg, msg.get_rect(center=(WIDTH/2, HEIGHT/2 - 50)))

            if draw_button('REINTENTAR', WIDTH/2 - 220, HEIGHT/2 + 50, 200, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: 'RETRY') == 'RETRY':
                gameLoop()
            if draw_button('MENU', WIDTH/2 + 20, HEIGHT/2 + 50, 200, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: 'MENU') == 'MENU':
                return

            draw_ui(base_score * score_multiplier)
            pygame.display.update()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in PAUSE_KEYS:
                    paused = not paused
                    continue
                if paused:
                    continue
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    candidate_direction = (-SNAKE_BLOCK, 0)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    candidate_direction = (SNAKE_BLOCK, 0)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    candidate_direction = (0, -SNAKE_BLOCK)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    candidate_direction = (0, SNAKE_BLOCK)
                else:
                    candidate_direction = None

                if candidate_direction is not None:
                    base_direction = pending_direction if pending_direction is not None else (dx, dy)
                    opposite_direction = (-base_direction[0], -base_direction[1])
                    if candidate_direction != base_direction and candidate_direction != opposite_direction:
                        pending_direction = candidate_direction
                        play_sound('cambio_de_direcion.mp3')

        if paused:
            last_move_time = now
            dis.fill(COLOR_BG)
            off = (SNAKE_BLOCK - FOOD_SIZE) / 2
            pygame.draw.rect(dis, COLOR_FOOD, [foodx + off, foody + off, FOOD_SIZE, FOOD_SIZE])
            if powerup:
                power_rect = pygame.Rect(powerup['pos'][0] + 2, powerup['pos'][1] + 2, SNAKE_BLOCK - 4, SNAKE_BLOCK - 4)
                pygame.draw.rect(dis, COLOR_POWERUP, power_rect)
                power_letter = font_label.render(get_powerup_name(powerup['type'])[0], True, COLOR_TEXT)
                dis.blit(power_letter, power_letter.get_rect(center=power_rect.center))
            for rect in obstacle_rects:
                pygame.draw.rect(dis, COLOR_OBSTACLE, rect)
            our_snake(SNAKE_BLOCK, get_smoothed_snake(snake_List, prev_snake_list, 1.0))
            draw_particles(particles)
            draw_ui(base_score * score_multiplier)
            draw_game_status(combo_count, active_effect_labels)
            draw_pause_overlay()
            pygame.display.update()
            clock.tick(FPS)
            continue

        speed_factor = 4 if BASE_SPEED == 40 else 6
        dynamic_speed = max(6, BASE_SPEED - (Length_of_snake // speed_factor))
        if 'rayo' in active_powerups:
            dynamic_speed += 5
        if 'tortuga' in active_powerups:
            dynamic_speed = max(4, dynamic_speed - 4)
        move_interval = 1000 / dynamic_speed
        move_progress = min(1.0, (now - last_move_time) / move_interval) if dx or dy else 1.0

        if 'iman' in active_powerups:
            if abs(foodx - x1) <= SNAKE_BLOCK * 6:
                foodx += SNAKE_BLOCK if x1 > foodx else -SNAKE_BLOCK if x1 < foodx else 0
            if abs(foody - y1) <= SNAKE_BLOCK * 6:
                foody += SNAKE_BLOCK if y1 > foody else -SNAKE_BLOCK if y1 < foody else 0
            foodx = max(0, min(WIDTH - SNAKE_BLOCK, foodx))
            foody = max(TOP_BAR_HEIGHT, min(HEIGHT - SNAKE_BLOCK, foody))
            if any(rect.colliderect(pygame.Rect(foodx, foody, SNAKE_BLOCK, SNAKE_BLOCK)) for rect in obstacle_rects):
                foodx, foody = get_safe_food_position(snake_List, obstacle_rects, [powerup['pos']] if powerup else None)

        if pending_direction is not None and dx == 0 and dy == 0:
            dx, dy = pending_direction
            pending_direction = None

        if (dx or dy or pending_direction is not None) and now - last_move_time >= move_interval:
            if pending_direction is not None:
                dx, dy = pending_direction
                pending_direction = None
            prev_snake_list = [segment[:] for segment in snake_List]
            x1 += dx
            y1 += dy
            last_move_time = now
            move_progress = 0.0

            if current_mode_id == "zen":
                if x1 >= WIDTH:
                    x1 = 0
                elif x1 < 0:
                    x1 = WIDTH - SNAKE_BLOCK
                if y1 >= HEIGHT:
                    y1 = TOP_BAR_HEIGHT
                elif y1 < TOP_BAR_HEIGHT:
                    y1 = HEIGHT - SNAKE_BLOCK
            elif x1 >= WIDTH or x1 < 0 or y1 >= HEIGHT or y1 < TOP_BAR_HEIGHT:
                game_close = True

            snake_Head = [x1, y1]
            snake_List.append(snake_Head)
            if len(snake_List) > Length_of_snake:
                del snake_List[0]

            if 'fantasma' not in active_powerups:
                for x in snake_List[:-1]:
                    if x == snake_Head:
                        game_close = True
            if any(rect.colliderect(pygame.Rect(x1, y1, SNAKE_BLOCK, SNAKE_BLOCK)) for rect in obstacle_rects):
                game_close = True

            if powerup and x1 == powerup['pos'][0] and y1 == powerup['pos'][1]:
                active_powerups[powerup['type']] = now + POWERUP_DURATION_MS
                powerup = None
                next_powerup_spawn = now + POWERUP_SPAWN_INTERVAL_MS

            if x1 == foodx and y1 == foody:
                combo_count = combo_count + 1 if now - last_food_time <= COMBO_WINDOW_MS else 1
                last_food_time = now
                combo_bonus = combo_count - 1
                base_score += 1 + combo_bonus
                fruits_collected += 1
                Length_of_snake += 1
                if current_mode_id == "time_attack":
                    time_attack_end += TIME_ATTACK_BONUS_MS
                particles.extend(create_food_particles(foodx, foody))
                blocked_for_obstacles = [[x1, y1], [foodx, foody]]
                if powerup:
                    blocked_for_obstacles.append(powerup['pos'])
                obstacle_rects = get_safe_obstacle_rects(snake_List, blocked_for_obstacles)
                blocked_positions = [[foodx, foody]]
                if powerup:
                    blocked_positions.append(powerup['pos'])
                foodx, foody = get_safe_food_position(snake_List, obstacle_rects, blocked_positions)
                if powerup:
                    powerup['pos'] = spawn_item(snake_List, obstacle_rects, [[foodx, foody], [x1, y1]])

        dis.fill(COLOR_BG)
        off = (SNAKE_BLOCK - FOOD_SIZE) / 2
        pygame.draw.rect(dis, COLOR_FOOD, [foodx + off, foody + off, FOOD_SIZE, FOOD_SIZE])
        if powerup:
            power_rect = pygame.Rect(powerup['pos'][0] + 2, powerup['pos'][1] + 2, SNAKE_BLOCK - 4, SNAKE_BLOCK - 4)
            pygame.draw.rect(dis, COLOR_POWERUP, power_rect)
            power_letter = font_label.render(get_powerup_name(powerup['type'])[0], True, COLOR_TEXT)
            dis.blit(power_letter, power_letter.get_rect(center=power_rect.center))
        for rect in obstacle_rects:
            pygame.draw.rect(dis, COLOR_OBSTACLE, rect)

        our_snake(SNAKE_BLOCK, get_smoothed_snake(snake_List, prev_snake_list, move_progress))
        draw_particles(particles)

        visual_score = base_score * score_multiplier
        update_daily_missions(current_mode_id, fruits_collected, visual_score)
        if visual_score > high_score:
            high_score = visual_score
            save_data()

        draw_ui(visual_score)
        draw_game_status(combo_count, active_effect_labels)
        pygame.display.update()
        clock.tick(FPS)

if __name__ == "__main__":
    preload_audio_async()
    main_menu()
