# Version 1.2.0

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

try:
    import requests
except ImportError:
    requests = None


def get_app_dir():
    """Devuelve la carpeta base persistente del juego."""
    if getattr(sys, "frozen", False):
        documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
        return ensure_directory(os.path.join(documents_dir, "GameSnake", "Game"))
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """Resuelve rutas de recursos tanto en desarrollo como empaquetado."""
    base_path = getattr(sys, "_MEIPASS", get_app_dir())
    return os.path.join(base_path, relative_path)


def ensure_directory(path):
    """Crea una carpeta si no existe."""
    os.makedirs(path, exist_ok=True)
    return path


def file_exists_and_has_data(path):
    """Comprueba que un archivo exista y no esté vacío."""
    return os.path.isfile(path) and os.path.getsize(path) > 0


def read_text_file(path, default_value=""):
    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            return file_obj.read().strip()
    except OSError:
        return default_value


def download_file(url, destination, timeout=5):
    """Descarga un archivo sin romper el juego si la red falla."""
    ensure_directory(os.path.dirname(destination))
    try:
        if requests is not None:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            with open(destination, "wb") as file_obj:
                file_obj.write(response.content)
            return True

        with urllib_request.urlopen(url, timeout=timeout) as response, open(destination, "wb") as file_obj:
            file_obj.write(response.read())
        return True
    except Exception:
        return False


def load_json_response(url, timeout=3, method="GET", payload=None):
    """Realiza una petición JSON tolerante a ausencia de red o requests."""
    try:
        if requests is not None:
            request_fn = requests.patch if method == "PATCH" else requests.get
            response = request_fn(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return True

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib_request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib_request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False

    return False


pygame.init()
AUDIO_AVAILABLE = True
try:
    pygame.mixer.init()
except pygame.error:
    AUDIO_AVAILABLE = False


COLOR_BG = (40, 40, 45)
COLOR_BG_ELEVATED = (24, 29, 40)
COLOR_GRID = (50, 55, 64)
COLOR_SNAKE = (46, 204, 113)
COLOR_SNAKE_HEAD = (39, 174, 96)
COLOR_FOOD = (231, 76, 60)
COLOR_TEXT = (236, 240, 241)
COLOR_TEXT_MUTED = (155, 165, 180)
COLOR_UI_BAR = (30, 30, 35)
COLOR_GOLD = (241, 196, 15)
COLOR_BUTTON = (52, 73, 94)
COLOR_BUTTON_HOVER = (93, 109, 126)

WIDTH = 1200
HEIGHT = 760
TOP_BAR_HEIGHT = 50
SNAKE_BLOCK = 20
FOOD_SIZE = 14

FPS = 60
BASE_SPEED = 15
REVIEW_DELAY_SECONDS = 300
PROJECT_ID = "reviw-snake"
APP_ID = "1:1864041655978:web:210a25c77f6efb6ef22ad3"
GAME_WEB_URL = "https://reviw-snake.web.app"
PLAYER_NAME = os.getenv("SNAKE_PLAYER_NAME", os.getenv("USERNAME", "Player"))
APP_DIR = get_app_dir()
RES_DIR = ensure_directory(os.path.join(APP_DIR, "res"))
DATA_FILE = os.path.join(APP_DIR, "snake_data.json")
VERSION_FILE = os.path.join(APP_DIR, "version.txt")
AUDIO_CACHE = {}

BACKGROUND_MUSIC_URL = "https://raw.githubusercontent.com/BluePandaOpn/Snake/main/res/fondo.mp3"
DIRECTION_SOUND_URL = "https://raw.githubusercontent.com/BluePandaOpn/Snake/main/res/cambio_de_direcion.mp3"
AUDIO_SOURCES = {
    "fondo.mp3": BACKGROUND_MUSIC_URL,
    "cambio_de_direcion.mp3": DIRECTION_SOUND_URL,
}


def resolve_runtime_resource(relative_path):
    """Busca primero recursos persistentes y luego los empaquetados."""
    candidate_paths = [
        os.path.join(APP_DIR, relative_path),
        get_resource_path(relative_path),
        get_resource_path(os.path.join("assets", relative_path)),
    ]
    for path in candidate_paths:
        if file_exists_and_has_data(path):
            return path
    return None


def ensure_audio_file(filename):
    """Devuelve la ruta usable del audio o None si no se pudo preparar."""
    sound_path = resolve_runtime_resource(os.path.join("res", filename))
    if sound_path:
        return sound_path

    cached_path = os.path.join(RES_DIR, filename)
    if file_exists_and_has_data(cached_path):
        return cached_path

    url = AUDIO_SOURCES.get(filename)
    if not url or not download_file(url, cached_path):
        return None

    return cached_path if file_exists_and_has_data(cached_path) else None


def get_sound(sound_name):
    """Carga y cachea efectos de sonido sin lanzar errores."""
    if not AUDIO_AVAILABLE:
        return None
    if sound_name in AUDIO_CACHE:
        return AUDIO_CACHE[sound_name]

    sound_path = ensure_audio_file(sound_name)
    if not sound_path:
        AUDIO_CACHE[sound_name] = None
        return None

    try:
        AUDIO_CACHE[sound_name] = pygame.mixer.Sound(sound_path)
    except pygame.error:
        AUDIO_CACHE[sound_name] = None
    return AUDIO_CACHE[sound_name]


def play_sound(sound_name):
    """Reproduce un efecto si el audio está disponible."""
    sound = get_sound(sound_name)
    if sound is None:
        return
    try:
        sound.play()
    except pygame.error:
        pass


def ensure_background_music():
    """Carga música de fondo local o desde GitHub con fallback silencioso."""
    if not AUDIO_AVAILABLE:
        return False

    music_path = ensure_audio_file("fondo.mp3")
    if not music_path:
        return False

    try:
        if pygame.mixer.music.get_busy():
            return True
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.45)
        pygame.mixer.music.play(-1)
        return True
    except pygame.error:
        return False


def preload_audio_async():
    """Intenta dejar el audio listo en segundo plano."""
    def worker():
        ensure_audio_file("fondo.mp3")
        ensure_audio_file("cambio_de_direcion.mp3")

    threading.Thread(target=worker, daemon=True).start()


dis = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Pro")
clock = pygame.time.Clock()
icon_path = resolve_runtime_resource("ico.ico") or resolve_runtime_resource(os.path.join("assets", "ico.ico"))
if icon_path:
    try:
        icon = pygame.image.load(icon_path)
        pygame.display.set_icon(icon)
    except pygame.error:
        pass

font_ui = pygame.font.SysFont("arial", 22, bold=True)
font_title = pygame.font.SysFont("arial", 80, bold=True)
font_gameover = pygame.font.SysFont("arial", 60, bold=True)
font_btn = pygame.font.SysFont("arial", 30, bold=True)
font_meta = pygame.font.SysFont("arial", 18, bold=False)


def exit_game():
    """Cierra pygame y termina el proceso de forma segura."""
    pygame.quit()
    sys.exit()


def load_data():
    """Carga el récord desde un archivo JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
                return data.get("high_score", 0)
        except Exception:
            return 0
    return 0


def save_data(score):
    """Guarda el nuevo récord en un archivo JSON."""
    data = {"high_score": score}
    with open(DATA_FILE, "w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj)


high_score = load_data()
review_prompt_shown = False
GAME_VERSION = read_text_file(VERSION_FILE, "dev")


def sanitize_player_name(name):
    """Limpia el nombre del jugador para usarlo en web y en el ranking."""
    cleaned = re.sub(r"\s+", " ", (name or "").strip())
    return cleaned[:24] or "Player"


def build_leaderboard_document_id(name):
    """Genera un id estable por jugador para actualizar su récord."""
    safe_name = sanitize_player_name(name).lower()
    safe_name = re.sub(r"[^a-z0-9_-]+", "-", safe_name).strip("-")
    return safe_name or "player"


def upload_score_to_web(name, score):
    """Sincroniza el récord con Firestore mediante la REST API."""
    player_name = sanitize_player_name(name)
    document_id = build_leaderboard_document_id(player_name)
    url = (
        f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/databases/(default)/documents/leaderboard/{document_id}"
    )
    payload = {
        "fields": {
            "name": {"stringValue": player_name},
            "score": {"integerValue": str(int(score))},
            "appId": {"stringValue": APP_ID},
            "updatedAt": {
                "timestampValue": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            },
        }
    }
    params = [
        ("updateMask.fieldPaths", "name"),
        ("updateMask.fieldPaths", "score"),
        ("updateMask.fieldPaths", "appId"),
        ("updateMask.fieldPaths", "updatedAt"),
    ]
    query = "&".join(f"{key}={value}" for key, value in params)
    return load_json_response(f"{url}?{query}", timeout=3, method="PATCH", payload=payload)


def sync_score_async(score):
    """Evita bloquear el juego al enviar el récord a la web."""
    threading.Thread(target=upload_score_to_web, args=(PLAYER_NAME, score), daemon=True).start()


def restore_game_window():
    """Restaura la ventana principal tras cerrar la mini ventana de reseña."""
    global dis
    dis = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Snake Pro")


def maybe_show_review_prompt(game_start_time):
    """Muestra la ventana de reseña una sola vez tras una sesión larga."""
    global review_prompt_shown

    if review_prompt_shown:
        return
    if time.time() - game_start_time < REVIEW_DELAY_SECONDS:
        return

    review_prompt_shown = True
    restore_game_window()


def is_inside(rect, pos):
    return rect.collidepoint(pos)


def draw_background_grid(offset=0):
    for x in range(0, WIDTH, SNAKE_BLOCK):
        pygame.draw.line(dis, COLOR_GRID, (x + (offset % SNAKE_BLOCK), TOP_BAR_HEIGHT), (x + (offset % SNAKE_BLOCK), HEIGHT))
    for y in range(TOP_BAR_HEIGHT, HEIGHT, SNAKE_BLOCK):
        pygame.draw.line(dis, COLOR_GRID, (0, y), (WIDTH, y))


def draw_ui(score):
    """Dibuja el sistema de puntos y récords con iconos simbólicos."""
    pygame.draw.rect(dis, COLOR_UI_BAR, [0, 0, WIDTH, TOP_BAR_HEIGHT])
    pygame.draw.rect(dis, COLOR_SNAKE, [20, 15, 15, 15])
    score_txt = font_ui.render(f": {score}", True, COLOR_TEXT)
    dis.blit(score_txt, [40, 12])

    pygame.draw.rect(dis, COLOR_GOLD, [130, 15, 15, 10])
    pygame.draw.rect(dis, COLOR_GOLD, [135, 25, 5, 10])
    pygame.draw.rect(dis, COLOR_GOLD, [132, 32, 11, 3])

    high_txt = font_ui.render(f": {high_score}", True, COLOR_GOLD)
    dis.blit(high_txt, [155, 12])


def draw_button(text, rect, inactive_color, active_color, mouse_pos):
    hovered = is_inside(rect, mouse_pos)
    pygame.draw.rect(dis, active_color if hovered else inactive_color, rect, border_radius=8)
    text_surf = font_btn.render(text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=rect.center)
    dis.blit(text_surf, text_rect)
    return hovered


def our_snake(snake_block, snake_list):
    """Dibuja la serpiente como cuadrados perfectos."""
    for index, segment in enumerate(snake_list):
        color = COLOR_SNAKE_HEAD if index == len(snake_list) - 1 else COLOR_SNAKE
        pygame.draw.rect(dis, color, [segment[0], segment[1], snake_block, snake_block], border_radius=4)


def spawn_food(snake_list):
    occupied = {tuple(segment) for segment in snake_list}
    while True:
        foodx = random.randrange(0, WIDTH - SNAKE_BLOCK + 1, SNAKE_BLOCK)
        foody = random.randrange(TOP_BAR_HEIGHT + SNAKE_BLOCK, HEIGHT - SNAKE_BLOCK + 1, SNAKE_BLOCK)
        if (foodx, foody) not in occupied:
            return foodx, foody


def loading_animation(duration=0.65):
    """Animación breve de preparación de partida."""
    start_time = time.time()
    phase = 0.0

    while time.time() - start_time < duration:
        dis.fill(COLOR_BG)
        draw_background_grid(int(phase * 6))

        title = font_btn.render("PREPARANDO PARTIDA", True, COLOR_TEXT)
        subtitle = font_meta.render("Cargando recursos y ajustando el tablero...", True, COLOR_TEXT_MUTED)
        dis.blit(title, title.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 72)))
        dis.blit(subtitle, subtitle.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 108)))

        for i in range(4):
            pulse = 8 + math.sin(phase + i * 0.45) * 6
            spacing = 30
            x_pos = (WIDTH / 2 - 50) + (i * spacing)
            y_pos = HEIGHT / 2 - pulse
            color = COLOR_SNAKE_HEAD if i == 3 else COLOR_SNAKE
            pygame.draw.rect(dis, color, [x_pos, y_pos, 22, 22], border_radius=6)

        pygame.display.update()
        phase += 0.15
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game()


def options_menu():
    """Pantalla de opciones."""
    global BASE_SPEED
    normal_rect = pygame.Rect(WIDTH / 2 - 125, 360, 250, 50)
    pro_rect = pygame.Rect(WIDTH / 2 - 125, 430, 250, 50)
    back_rect = pygame.Rect(WIDTH / 2 - 125, 520, 250, 50)

    while True:
        mouse_pos = pygame.mouse.get_pos()
        dis.fill(COLOR_BG)
        draw_background_grid()

        title_text = font_title.render("OPCIONES", True, COLOR_TEXT)
        dis.blit(title_text, title_text.get_rect(center=(WIDTH / 2, 160)))

        info_text = font_btn.render(f"Velocidad Inicial: {BASE_SPEED}", True, COLOR_TEXT)
        dis.blit(info_text, info_text.get_rect(center=(WIDTH / 2, 270)))

        desc_text = font_ui.render("Normal mantiene más control. Pro acelera la reacción.", True, COLOR_SNAKE)
        dis.blit(desc_text, desc_text.get_rect(center=(WIDTH / 2, 315)))

        draw_button("Modo Normal (15)", normal_rect, COLOR_BUTTON, COLOR_BUTTON_HOVER, mouse_pos)
        draw_button("Modo Pro (25)", pro_rect, COLOR_BUTTON, COLOR_BUTTON_HOVER, mouse_pos)
        draw_button("Volver al Menú", back_rect, COLOR_UI_BAR, COLOR_BUTTON_HOVER, mouse_pos)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_inside(normal_rect, event.pos):
                    BASE_SPEED = 15
                elif is_inside(pro_rect, event.pos):
                    BASE_SPEED = 25
                elif is_inside(back_rect, event.pos):
                    return

        clock.tick(FPS)


def main_menu():
    """Pantalla del menú principal con control de clics limpio."""
    ensure_background_music()
    play_rect = pygame.Rect(WIDTH / 2 - 100, 320, 200, 60)
    options_rect = pygame.Rect(WIDTH / 2 - 100, 410, 200, 60)
    exit_rect = pygame.Rect(WIDTH / 2 - 100, 500, 200, 60)
    grid_offset = 0

    while True:
        mouse_pos = pygame.mouse.get_pos()
        dis.fill(COLOR_BG)
        draw_background_grid(grid_offset)
        grid_offset = (grid_offset + 1) % SNAKE_BLOCK

        title_text = font_title.render("SNAKE PRO", True, COLOR_SNAKE)
        title_rect = title_text.get_rect(center=(WIDTH / 2, 180))
        dis.blit(title_text, title_rect)

        version_text = font_meta.render(f"Version {GAME_VERSION}", True, COLOR_TEXT_MUTED)
        dis.blit(version_text, version_text.get_rect(center=(WIDTH / 2, 240)))

        draw_button("JUGAR", play_rect, COLOR_BUTTON, COLOR_BUTTON_HOVER, mouse_pos)
        draw_button("OPCIONES", options_rect, COLOR_BUTTON, COLOR_BUTTON_HOVER, mouse_pos)
        draw_button("SALIR", exit_rect, COLOR_BUTTON, COLOR_BUTTON_HOVER, mouse_pos)

        for i in range(10):
            pygame.draw.rect(dis, COLOR_SNAKE, [WIDTH / 2 - 100 + (i * 20), 620, 18, 18], border_radius=4)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_inside(play_rect, event.pos):
                    return "play"
                if is_inside(options_rect, event.pos):
                    options_menu()
                if is_inside(exit_rect, event.pos):
                    return "exit"

        clock.tick(FPS)


def game_over_screen(score):
    retry_rect = pygame.Rect(WIDTH / 2 - 220, HEIGHT / 2 + 50, 200, 50)
    menu_rect = pygame.Rect(WIDTH / 2 + 20, HEIGHT / 2 + 50, 200, 50)

    while True:
        mouse_pos = pygame.mouse.get_pos()
        dis.fill(COLOR_BG)
        draw_background_grid()

        msg = font_gameover.render("FIN DEL JUEGO", True, COLOR_FOOD)
        dis.blit(msg, msg.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 70)))

        score_text = font_btn.render(f"Puntuación final: {score}", True, COLOR_TEXT)
        dis.blit(score_text, score_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 10)))

        draw_button("REINTENTAR", retry_rect, COLOR_BUTTON, COLOR_BUTTON_HOVER, mouse_pos)
        draw_button("MENÚ", menu_rect, COLOR_BUTTON, COLOR_BUTTON_HOVER, mouse_pos)
        draw_ui(score)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_inside(retry_rect, event.pos):
                    return "retry"
                if is_inside(menu_rect, event.pos):
                    return "menu"

        clock.tick(FPS)


def gameLoop():
    """Bucle principal del juego con velocidad dinámica."""
    global high_score

    game_start_time = time.time()
    x1 = (WIDTH // 2 // SNAKE_BLOCK) * SNAKE_BLOCK
    y1 = ((HEIGHT // 2) // SNAKE_BLOCK) * SNAKE_BLOCK
    x1_change = 0
    y1_change = 0
    snake_list = []
    length_of_snake = 1
    record_dirty = False

    foodx, foody = spawn_food(snake_list)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a) and x1_change == 0:
                    x1_change, y1_change = -SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and x1_change == 0:
                    x1_change, y1_change = SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")
                elif event.key in (pygame.K_UP, pygame.K_w) and y1_change == 0:
                    y1_change, x1_change = -SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")
                elif event.key in (pygame.K_DOWN, pygame.K_s) and y1_change == 0:
                    y1_change, x1_change = SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")

        x1 += x1_change
        y1 += y1_change

        if x1 >= WIDTH or x1 < 0 or y1 >= HEIGHT or y1 < TOP_BAR_HEIGHT:
            if record_dirty:
                sync_score_async(high_score)
            return game_over_screen(length_of_snake - 1)

        snake_head = [x1, y1]
        snake_list.append(snake_head)
        if len(snake_list) > length_of_snake:
            del snake_list[0]

        if snake_head in snake_list[:-1]:
            if record_dirty:
                sync_score_async(high_score)
            return game_over_screen(length_of_snake - 1)

        dis.fill(COLOR_BG)
        draw_background_grid()

        offset = (SNAKE_BLOCK - FOOD_SIZE) / 2
        pygame.draw.rect(dis, COLOR_FOOD, [foodx + offset, foody + offset, FOOD_SIZE, FOOD_SIZE], border_radius=4)
        our_snake(SNAKE_BLOCK, snake_list)

        current_score = length_of_snake - 1
        if current_score > high_score:
            high_score = current_score
            save_data(high_score)
            record_dirty = True

        draw_ui(current_score)
        pygame.display.update()

        if x1 == foodx and y1 == foody:
            length_of_snake += 1
            foodx, foody = spawn_food(snake_list)

        dynamic_speed = max(6, BASE_SPEED - (length_of_snake // 6))
        maybe_show_review_prompt(game_start_time)
        clock.tick(dynamic_speed)


if __name__ == "__main__":
    preload_audio_async()

    while True:
        menu_action = main_menu()
        if menu_action == "exit":
            break

        if menu_action == "play":
            loading_animation()
            while True:
                result = gameLoop()
                if result == "retry":
                    loading_animation(0.45)
                    continue
                if result == "menu":
                    break
                if result == "exit":
                    exit_game()

    exit_game()
