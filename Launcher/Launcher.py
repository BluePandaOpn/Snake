import os
import requests
import subprocess
import tkinter as tk
import customtkinter as ctk
from plyer import notification
from threading import Thread

# --- CONFIGURACIÓN ---
USER_PROFILE = os.path.expanduser('~')
RUTA_CARPETA = os.path.join(USER_PROFILE, 'Documents', 'SnakeGame')
EJECUTABLE_PATH = os.path.join(RUTA_CARPETA, 'Snake.exe')
VERSION_LOCAL_PATH = os.path.join(RUTA_CARPETA, 'version.txt')

# URLs de tu repositorio
URL_EXE = "https://github.com/BluePandaOpn/Snake/raw/main/bin/Snake.exe"
URL_VERSION_RAW = "https://raw.githubusercontent.com/BluePandaOpn/Snake/main/version.txt"

# Colores del Juego
COLOR_BG = "#28282d"        # Gris oscuro
COLOR_SNAKE = "#2ecc71"     # Verde Esmeralda
COLOR_SNAKE_HEAD = "#27ae60" # Verde oscuro

class SnakeLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. ELIMINAR PANEL SUPERIOR (Sin bordes/Título)
        self.overrideredirect(True)
        
        # 2. CONFIGURACIÓN Y CENTRADO
        self.width = 400
        self.height = 450
        self.centrar_ventana()
        
        self.configure(fg_color=COLOR_BG)
        ctk.set_appearance_mode("dark")

        # UI Elements
        self.label_titulo = ctk.CTkLabel(self, text="SNAKE ENGINE", font=("Arial", 24, "bold"), text_color="white")
        self.label_titulo.pack(pady=(30, 10))

        # 3. ANIMACIÓN DE GUSANO (Cuadrícula 2x2)
        self.canvas = tk.Canvas(self, width=120, height=120, bg=COLOR_BG, highlightthickness=0)
        self.canvas.pack(pady=20)

        self.posiciones = [(20, 20), (70, 20), (70, 70), (20, 70)]
        self.segmentos_indices = [0, 1, 2] 
        self.rects = []

        for i in range(3):
            x, y = self.posiciones[self.segmentos_indices[i]]
            color = COLOR_SNAKE_HEAD if i == 2 else COLOR_SNAKE
            r = self.canvas.create_rectangle(x, y, x+30, y+30, fill=color, outline="")
            self.rects.append(r)

        self.label_estado = ctk.CTkLabel(self, text="Buscando actualizaciones...", font=("Arial", 13), text_color=COLOR_SNAKE)
        self.label_estado.pack(pady=5)

        self.label_detalles = ctk.CTkLabel(self, text="Iniciando conexión...", font=("Arial", 11), text_color="gray")
        self.label_detalles.pack(pady=(0, 20))

        # Iniciar hilos
        self.animar_gusano()
        Thread(target=self.proceso_principal, daemon=True).start()

    def centrar_ventana(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (self.width // 2)
        y = (screen_height // 2) - (self.height // 2)
        self.geometry(f'{self.width}x{self.height}+{x}+{y}')

    def animar_gusano(self):
        todas = {0, 1, 2, 3}
        ocupadas = set(self.segmentos_indices)
        vacia = list(todas - ocupadas)[0]

        # Mover cola a la posición vacía para que sea la nueva cabeza
        self.segmentos_indices.pop(0)
        self.segmentos_indices.append(vacia)

        for i in range(3):
            pos_idx = self.segmentos_indices[i]
            nx, ny = self.posiciones[pos_idx]
            self.canvas.coords(self.rects[i], nx, ny, nx+30, ny+30)

        self.after(350, self.animar_gusano)

    def enviar_notificacion(self, titulo, mensaje):
        try:
            notification.notify(title=titulo, message=mensaje, app_name='Snake Launcher', timeout=5)
        except: pass

    def proceso_principal(self):
        if not os.path.exists(RUTA_CARPETA):
            os.makedirs(RUTA_CARPETA)

        try:
            self.label_detalles.configure(text="Consultando versión en GitHub...")
            respuesta_v = requests.get(URL_VERSION_RAW, timeout=10)
            v_remota = respuesta_v.text.strip()
            
            v_local = ""
            if os.path.exists(VERSION_LOCAL_PATH):
                with open(VERSION_LOCAL_PATH, 'r') as f:
                    v_local = f.read().strip()

            if v_local != v_remota:
                self.label_estado.configure(text="¡Nueva versión disponible!")
                self.enviar_notificacion("Snake Update", f"Descargando versión {v_remota}...")
                
                response = requests.get(URL_EXE, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                
                descargado = 0
                with open(EJECUTABLE_PATH, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            descargado += len(chunk)
                            if total_size > 0:
                                p = int((descargado / total_size) * 100)
                                self.label_detalles.configure(text=f"Descargando: {p}%")

                with open(VERSION_LOCAL_PATH, 'w') as f:
                    f.write(v_remota)
                self.label_estado.configure(text="Actualización finalizada")
            else:
                self.label_estado.configure(text="Juego actualizado")
                self.label_detalles.configure(text=f"Versión actual: {v_local}")

        except Exception as e:
            self.label_estado.configure(text="Modo Offline")
            self.label_detalles.configure(text="No se pudo verificar la versión")

        self.ejecutar_juego()

    def ejecutar_juego(self):
        if os.path.exists(EJECUTABLE_PATH):
            self.label_detalles.configure(text="Iniciando Snake...")
            subprocess.Popen([EJECUTABLE_PATH], cwd=RUTA_CARPETA)
            self.after(1500, self.destroy)
        else:
            self.label_estado.configure(text="Error fatal", text_color="red")
            self.label_detalles.configure(text="Snake.exe no encontrado.")

if __name__ == "__main__":
    app = SnakeLauncher()
    app.mainloop()