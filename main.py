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

WIDTH = 1200
HEIGHT = 760
TOP_BAR_HEIGHT = 50
SNAKE_BLOCK = 20
FOOD_SIZE = 14
FPS = 60

dis = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Snake Pro - Ultimate Edition')
clock = pygame.time.Clock()

font_ui = pygame.font.SysFont("arial", 22, bold=True)
font_title = pygame.font.SysFont("arial", 80, bold=True)
font_gameover = pygame.font.SysFont("arial", 60, bold=True)
font_btn = pygame.font.SysFont("arial", 30, bold=True)
font_label = pygame.font.SysFont("arial", 24, bold=True)

DATA_FILE = os.path.join(APP_DIR, "snake_data.json")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f).get("high_score", 0)
        except: return 0
    return 0

def save_data(score):
    with open(DATA_FILE, "w") as f:
        json.dump({"high_score": score}, f)

high_score = load_data()

def draw_ui(score):
    pygame.draw.rect(dis, COLOR_UI_BAR, [0, 0, WIDTH, TOP_BAR_HEIGHT])
    pygame.draw.rect(dis, COLOR_SNAKE, [20, 15, 15, 15])
    dis.blit(font_ui.render(f": {score}", True, COLOR_TEXT), [40, 12])
    pygame.draw.rect(dis, COLOR_GOLD, [130, 15, 15, 10]) 
    pygame.draw.rect(dis, COLOR_GOLD, [135, 25, 5, 10])  
    pygame.draw.rect(dis, COLOR_GOLD, [132, 32, 11, 3])  
    dis.blit(font_ui.render(f": {high_score}", True, COLOR_GOLD), [155, 12])

def our_snake(snake_block, snake_list):
    """Dibuja la serpiente como CUADRADOS PERFECTOS."""
    for i, x in enumerate(snake_list):
        color = COLOR_SNAKE_HEAD if i == len(snake_list) - 1 else COLOR_SNAKE
        pygame.draw.rect(dis, color, [x[0], x[1], snake_block, snake_block])

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
    global BASE_SPEED, SOUND_ENABLED, GRAPHICS_HIGH
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

        # BOTÓN VOLVER
        if draw_button("VOLVER AL MENÚ", WIDTH/2 - 150, 550, 300, 60, COLOR_UI_BAR, COLOR_BUTTON_HOVER, lambda: "BACK") == "BACK":
            running = False

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        clock.tick(FPS)

def main_menu():
    ensure_background_music()
    while True:
        dis.fill(COLOR_BG)
        title = font_title.render("SNAKE PRO", True, COLOR_SNAKE)
        dis.blit(title, title.get_rect(center=(WIDTH/2, 180)))
        
        if draw_button("JUGAR", WIDTH/2 - 100, 320, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "PLAY") == "PLAY":
            loading_animation()
            gameLoop()
        if draw_button("OPCIONES", WIDTH/2 - 100, 410, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "OPT") == "OPT":
            options_menu()
        if draw_button("SALIR", WIDTH/2 - 100, 500, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "EXIT") == "EXIT":
            pygame.quit(); sys.exit()

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        clock.tick(FPS)

def gameLoop():
    global high_score
    game_over = False
    game_close = False
    
    x1, y1 = (WIDTH // 2 // 20) * 20, (HEIGHT // 2 // 20) * 20
    dx, dy = 0, 0
    snake_List = []
    Length_of_snake = 1

    foodx = round(random.randrange(SNAKE_BLOCK, WIDTH - SNAKE_BLOCK) / 20.0) * 20.0
    foody = round(random.randrange(TOP_BAR_HEIGHT + SNAKE_BLOCK, HEIGHT - SNAKE_BLOCK) / 20.0) * 20.0

    while not game_over:
        while game_close:
            dis.fill(COLOR_BG)
            msg = font_gameover.render("FIN DEL JUEGO", True, COLOR_FOOD)
            dis.blit(msg, msg.get_rect(center=(WIDTH/2, HEIGHT/2 - 50)))
            
            if draw_button("REINTENTAR", WIDTH/2 - 220, HEIGHT/2 + 50, 200, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "RETRY") == "RETRY":
                gameLoop()
            if draw_button("MENÚ", WIDTH/2 + 20, HEIGHT/2 + 50, 200, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: "MENU") == "MENU":
                return
            
            draw_ui(Length_of_snake - 1)
            pygame.display.update()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: pygame.quit(); sys.exit()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a) and dx == 0:
                    dx, dy = -SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and dx == 0:
                    dx, dy = SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")
                elif event.key in (pygame.K_UP, pygame.K_w) and dy == 0:
                    dy, dx = -SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")
                elif event.key in (pygame.K_DOWN, pygame.K_s) and dy == 0:
                    dy, dx = SNAKE_BLOCK, 0
                    play_sound("cambio_de_direcion.mp3")

        if x1 >= WIDTH or x1 < 0 or y1 >= HEIGHT or y1 < TOP_BAR_HEIGHT:
            game_close = True
        
        x1 += dx
        y1 += dy
        dis.fill(COLOR_BG)
        
        off = (SNAKE_BLOCK - FOOD_SIZE) / 2
        pygame.draw.rect(dis, COLOR_FOOD, [foodx + off, foody + off, FOOD_SIZE, FOOD_SIZE])
        
        snake_Head = [x1, y1]
        snake_List.append(snake_Head)
        if len(snake_List) > Length_of_snake:
            del snake_List[0]

        for x in snake_List[:-1]:
            if x == snake_Head: game_close = True

        our_snake(SNAKE_BLOCK, snake_List)
        
        score = Length_of_snake - 1
        if score > high_score:
            high_score = score
            save_data(high_score)
            
        draw_ui(score)
        pygame.display.update()

        if x1 == foodx and y1 == foody:
            foodx = round(random.randrange(SNAKE_BLOCK, WIDTH - SNAKE_BLOCK) / 20.0) * 20.0
            foody = round(random.randrange(TOP_BAR_HEIGHT + SNAKE_BLOCK, HEIGHT - SNAKE_BLOCK) / 20.0) * 20.0
            Length_of_snake += 1

        # En dificultad infernal la velocidad escala más rápido
        speed_factor = 4 if BASE_SPEED == 40 else 6
        dynamic_speed = max(6, BASE_SPEED - (Length_of_snake // speed_factor))
        clock.tick(dynamic_speed)

if __name__ == "__main__":
    preload_audio_async()
    main_menu()