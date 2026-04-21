#Versinon 1.3
# Cambion: integracion de sistema de esquins integracion del sistenioma de reseñas integracino de sistema de monedas integracion de mas sistemas 


import pygame
import random
import time
import json
import os
import math
import re
import threading
from datetime import datetime, timezone

import requests
#import lib.PyinstallGame.reviw as reviw

# --- CONFIGURACIÓN INICIAL ---
pygame.init()
pygame.mixer.init()

# Paleta de Colores Solicitada
COLOR_BG = (40, 40, 45)        # Gris oscuro
COLOR_SNAKE = (46, 204, 113)   # Verde Esmeralda (Cuerpo)
COLOR_SNAKE_HEAD = (39, 174, 96) # Verde un poco más oscuro para la cabeza
COLOR_FOOD = (231, 76, 60)     # Rojo para la manzana cuadrada
COLOR_TEXT = (236, 240, 241)   # Blanco grisáceo para textos
COLOR_UI_BAR = (30, 30, 35)    # Fondo de la barra de UI
COLOR_GOLD = (241, 196, 15)    # Dorado para el récord (copa)
COLOR_BUTTON = (52, 73, 94)    # Color para los botones
COLOR_BUTTON_HOVER = (93, 109, 126) # Color al pasar el mouse

# Dimensiones de la Ventana
WIDTH = 1200
HEIGHT = 760
SNAKE_BLOCK = 20
FOOD_SIZE = 14  # Manzanas cuadradas más pequeñas

# Configuración de Rendimiento
FPS = 60
BASE_SPEED = 15 # Velocidad base inicial
REVIEW_DELAY_SECONDS = 5
PROJECT_ID = "reviw-snake"
APP_ID = "1:1864041655978:web:210a25c77f6efb6ef22ad3"
GAME_WEB_URL = "https://reviw-snake.web.app"
PLAYER_NAME = os.getenv("SNAKE_PLAYER_NAME", os.getenv("USERNAME", "Player"))

# Inicialización de la Pantalla
dis = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Snake Pro - Edición Minimalista')
clock = pygame.time.Clock()
icon = pygame.image.load('ico.ico') 
pygame.display.set_icon(icon)

# Fuentes
font_ui = pygame.font.SysFont("arial", 22, bold=True)
font_title = pygame.font.SysFont("arial", 80, bold=True)
font_gameover = pygame.font.SysFont("arial", 60, bold=True)
font_btn = pygame.font.SysFont("arial", 30, bold=True)

# --- SISTEMA DE DATOS (JSON) ---
DATA_FILE = "snake_data.json"

def load_data():
    """Carga el récord desde un archivo JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data.get("high_score", 0)
        except:
            return 0
    return 0

def save_data(score):
    """Guarda el nuevo récord en un archivo JSON."""
    data = {"high_score": score}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Variable global para el récord
high_score = load_data()
review_prompt_shown = False


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

    try:
        response = requests.patch(url, params=params, json=payload, timeout=3)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def sync_score_async(score):
    """Evita bloquear el juego al enviar el récord a la web."""
    threading.Thread(
        target=upload_score_to_web,
        args=(PLAYER_NAME, score),
        daemon=True,
    ).start()


def restore_game_window():
    """Restaura la ventana principal tras cerrar la mini ventana de reseña."""
    global dis
    dis = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Snake Pro - Edición Minimalista')


def maybe_show_review_prompt(game_start_time):
    """Muestra la ventana de reseña una sola vez tras 5 minutos de partida."""
    global review_prompt_shown

    if review_prompt_shown:
        return
    if time.time() - game_start_time < REVIEW_DELAY_SECONDS:
        return

    review_prompt_shown = True
    #reviw.main(project_name="Snake Pro", website_url=GAME_WEB_URL)
    restore_game_window()

def draw_ui(score):
    """Dibuja el sistema de puntos y récords con iconos simbólicos."""
    pygame.draw.rect(dis, COLOR_UI_BAR, [0, 0, WIDTH, 50])
    
    # Dibujar "Puntos"
    pygame.draw.rect(dis, COLOR_SNAKE, [20, 15, 15, 15])
    score_txt = font_ui.render(f": {score}", True, COLOR_TEXT)
    dis.blit(score_txt, [40, 12])
    
    # Dibujar "Copa/Récord"
    pygame.draw.rect(dis, COLOR_GOLD, [130, 15, 15, 10]) 
    pygame.draw.rect(dis, COLOR_GOLD, [135, 25, 5, 10])  
    pygame.draw.rect(dis, COLOR_GOLD, [132, 32, 11, 3])  
    
    high_txt = font_ui.render(f": {high_score}", True, COLOR_GOLD)
    dis.blit(high_txt, [155, 12])

def our_snake(snake_block, snake_list):
    """Dibuja la serpiente como cuadrados perfectos."""
    for i, x in enumerate(snake_list):
        color = COLOR_SNAKE_HEAD if i == len(snake_list) - 1 else COLOR_SNAKE
        pygame.draw.rect(dis, color, [x[0], x[1], snake_block, snake_block])

def loading_animation():
    """Animación de carga fluida y calmada con 4 cuadrados juntos."""
    loading = True
    start_time = time.time()
    t = 0
    
    while loading:
        dis.fill(COLOR_BG)
        
        elapsed = time.time() - start_time
        if elapsed > 2.5:  # Un poco más de tiempo para que sea fluido
            loading = False

        # Texto de carga
        load_txt = font_btn.render("CARGANDO...", True, COLOR_TEXT)
        dis.blit(load_txt, load_txt.get_rect(center=(WIDTH/2, HEIGHT/2 + 80)))

        # Animación de 4 cuadrados con movimiento de "pulso" u onda suave
        for i in range(4):
            # Movimiento de onda vertical suave, cuadrados pegados
            offset_y = math.sin(t + (i * 0.5)) * 10
            spacing = 22 # Casi pegados (SNAKE_BLOCK es 20)
            
            x_pos = (WIDTH / 2 - 44) + (i * spacing)
            y_pos = (HEIGHT / 2 - 10) + offset_y
            
            color = COLOR_SNAKE_HEAD if i == 3 else COLOR_SNAKE
            pygame.draw.rect(dis, color, [x_pos, y_pos, 20, 20])

        t += 0.1
        pygame.display.update()
        clock.tick(FPS)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

def draw_button(text, x, y, w, h, inactive_color, active_color, action=None):
    """Dibuja un botón interactivo y detecta clics."""
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    
    if x + w > mouse[0] > x and y + h > mouse[1] > y:
        pygame.draw.rect(dis, active_color, (x, y, w, h), border_radius=5)
        if click[0] == 1 and action is not None:
            time.sleep(0.1) 
            if action == gameLoop:
                loading_animation()
            action()
    else:
        pygame.draw.rect(dis, inactive_color, (x, y, w, h), border_radius=5)

    text_surf = font_btn.render(text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=((x + (w / 2)), (y + (h / 2))))
    dis.blit(text_surf, text_rect)

def options_menu():
    """Pantalla de Opciones."""
    options = True
    global BASE_SPEED
    while options:
        dis.fill(COLOR_BG)
        title_text = font_title.render("OPCIONES", True, COLOR_TEXT)
        dis.blit(title_text, title_text.get_rect(center=(WIDTH/2, 150)))
        
        info_text = font_btn.render(f"Velocidad Inicial: {BASE_SPEED}", True, COLOR_TEXT)
        dis.blit(info_text, info_text.get_rect(center=(WIDTH/2, 280)))
        
        desc_text = font_ui.render("(La serpiente se vuelve más lenta al crecer)", True, COLOR_SNAKE)
        dis.blit(desc_text, desc_text.get_rect(center=(WIDTH/2, 320)))

        draw_button("Modo Normal (15)", WIDTH/2 - 125, 380, 250, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: set_speed(15))
        draw_button("Modo Pro (25)", WIDTH/2 - 125, 450, 250, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, lambda: set_speed(25))
        draw_button("Volver al Menú", WIDTH/2 - 125, 550, 250, 50, COLOR_UI_BAR, COLOR_BUTTON_HOVER, lambda: "return")

        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: options = False
        
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        if WIDTH/2 - 125 + 250 > mouse[0] > WIDTH/2 - 125 and 550 + 50 > mouse[1] > 550:
            if click[0] == 1: options = False

def set_speed(s):
    global BASE_SPEED
    BASE_SPEED = s

def main_menu():
    """Pantalla del Menú Principal con Botones."""
    menu = True
    while menu:
        dis.fill(COLOR_BG)
        
        title_text = font_title.render("SNAKE PRO", True, COLOR_SNAKE)
        title_rect = title_text.get_rect(center=(WIDTH/2, 180))
        dis.blit(title_text, title_rect)
        
        draw_button("JUGAR", WIDTH/2 - 100, 320, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, gameLoop)
        draw_button("OPCIONES", WIDTH/2 - 100, 410, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, options_menu)
        draw_button("SALIR", WIDTH/2 - 100, 500, 200, 60, COLOR_BUTTON, COLOR_BUTTON_HOVER, quit)

        # Decoración inferior
        for i in range(10):
            pygame.draw.rect(dis, COLOR_SNAKE, [WIDTH/2 - 100 + (i*20), 620, 18, 18])

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

def gameLoop():
    """Bucle principal del juego con velocidad dinámica."""
    global high_score
    game_over = False
    game_close = False
    game_start_time = time.time()
    
    x1, y1 = WIDTH / 2, HEIGHT / 2
    x1_change, y1_change = 0, 0
    snake_List = []
    Length_of_snake = 1

    foodx = round(random.randrange(50, WIDTH - SNAKE_BLOCK - 50) / 20.0) * 20.0
    foody = round(random.randrange(70, HEIGHT - SNAKE_BLOCK - 50) / 20.0) * 20.0

    while not game_over:
        while game_close:
            dis.fill(COLOR_BG)
            msg = font_gameover.render("FIN DEL JUEGO", True, COLOR_FOOD)
            dis.blit(msg, msg.get_rect(center=(WIDTH/2, HEIGHT/2 - 50)))
            
            draw_button("REINTENTAR", WIDTH/2 - 220, HEIGHT/2 + 50, 200, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, gameLoop)
            draw_button("MENÚ", WIDTH/2 + 20, HEIGHT/2 + 50, 200, 50, COLOR_BUTTON, COLOR_BUTTON_HOVER, main_menu)
            
            draw_ui(Length_of_snake - 1)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and x1_change == 0:
                    x1_change, y1_change = -SNAKE_BLOCK, 0
                elif event.key == pygame.K_RIGHT and x1_change == 0:
                    x1_change, y1_change = SNAKE_BLOCK, 0
                elif event.key == pygame.K_UP and y1_change == 0:
                    y1_change, x1_change = -SNAKE_BLOCK, 0
                elif event.key == pygame.K_DOWN and y1_change == 0:
                    y1_change, x1_change = SNAKE_BLOCK, 0

        if x1 >= WIDTH or x1 < 0 or y1 >= HEIGHT or y1 < 50:
            game_close = True
        
        x1 += x1_change
        y1 += y1_change
        dis.fill(COLOR_BG)
        
        offset = (SNAKE_BLOCK - FOOD_SIZE) / 2
        pygame.draw.rect(dis, COLOR_FOOD, [foodx + offset, foody + offset, FOOD_SIZE, FOOD_SIZE])
        
        snake_Head = [x1, y1]
        snake_List.append(snake_Head)
        if len(snake_List) > Length_of_snake:
            del snake_List[0]

        for x in snake_List[:-1]:
            if x == snake_Head:
                game_close = True

        our_snake(SNAKE_BLOCK, snake_List)
        
        current_score = Length_of_snake - 1
        if current_score > high_score:
            high_score = current_score
            save_data(high_score)
            sync_score_async(high_score)
            
        draw_ui(current_score)
        pygame.display.update()

        if x1 == foodx and y1 == foody:
            foodx = round(random.randrange(50, WIDTH - SNAKE_BLOCK - 50) / 20.0) * 20.0
            foody = round(random.randrange(70, HEIGHT - SNAKE_BLOCK - 50) / 20.0) * 20.0
            Length_of_snake += 1

        # --- MECÁNICA DE VELOCIDAD DINÁMICA ---
        # A más longitud, menor velocidad. 
        # La velocidad mínima se bloquea en 5 para que no sea injugable.
        dynamic_speed = max(5, BASE_SPEED - (Length_of_snake // 5))
        maybe_show_review_prompt(game_start_time)
        
        clock.tick(FPS)
        time.sleep(max(0, 1/dynamic_speed - 1/FPS))

if __name__ == "__main__":
    main_menu()
