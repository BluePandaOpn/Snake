import os
import requests
import subprocess
import tkinter as tk
import customtkinter as ctk
from plyer import notification
from threading import Thread

# --- CONFIGURACIÓN ---
USER_PROFILE = os.path.expanduser('~')
# Se crea la carpeta en Documentos
RUTA_CARPETA = os.path.join(USER_PROFILE, 'Documents', 'SnakeGame')
EJECUTABLE_PATH = os.path.join(RUTA_CARPETA, 'Snake.exe')
VERSION_LOCAL_PATH = os.path.join(RUTA_CARPETA, 'version.txt')

# URLs de tu repositorio
URL_EXE = "https://github.com/BluePandaOpn/Snake/raw/main/bin/Snake.exe"
URL_VERSION_RAW = "https://raw.githubusercontent.com/BluePandaOpn/Snake/main/version.txt"

class SnakeLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana
        self.title("Snake Game Launcher")
        self.geometry("450x250")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # UI Elements
        self.label_titulo = ctk.CTkLabel(self, text="SNAKE ENGINE", font=("Orbitron", 20, "bold"))
        self.label_titulo.pack(pady=(20, 10))

        self.label_estado = ctk.CTkLabel(self, text="Buscando actualizaciones...", font=("Arial", 12))
        self.label_estado.pack(pady=5)

        self.progress = ctk.CTkProgressBar(self, width=350)
        self.progress.set(0)
        self.progress.pack(pady=15)

        self.label_detalles = ctk.CTkLabel(self, text="Iniciando conexión...", font=("Arial", 10), text_color="gray")
        self.label_detalles.pack()

        # Iniciar hilo de actualización
        Thread(target=self.proceso_principal, daemon=True).start()

    def enviar_notificacion(self, titulo, mensaje):
        try:
            notification.notify(
                title=titulo,
                message=mensaje,
                app_name='Snake Launcher',
                timeout=5
            )
        except:
            pass # Si falla la notificación, el programa sigue

    def proceso_principal(self):
        # 1. Asegurar que la carpeta existe
        if not os.path.exists(RUTA_CARPETA):
            os.makedirs(RUTA_CARPETA)

        try:
            # 2. Comprobar Versión
            self.label_detalles.configure(text="Consultando versión en GitHub...")
            respuesta_v = requests.get(URL_VERSION_RAW, timeout=10)
            v_remota = respuesta_v.text.strip()
            
            v_local = ""
            if os.path.exists(VERSION_LOCAL_PATH):
                with open(VERSION_LOCAL_PATH, 'r') as f:
                    v_local = f.read().strip()

            # 3. Comparar y Descargar
            if v_local != v_remota:
                self.label_estado.configure(text="¡Actualización encontrada!")
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
                                porcentaje = descargado / total_size
                                self.progress.set(porcentaje)
                                self.label_detalles.configure(text=f"Descargando: {int(porcentaje*100)}%")

                # Guardar nueva versión
                with open(VERSION_LOCAL_PATH, 'w') as f:
                    f.write(v_remota)
                
                self.label_estado.configure(text="Actualización finalizada")
            else:
                self.progress.set(1)
                self.label_estado.configure(text="El juego está actualizado")
                self.label_detalles.configure(text="Versión: " + v_local)

        except Exception as e:
            self.label_estado.configure(text="Modo Offline")
            self.label_detalles.configure(text="No se pudo verificar la versión")
            print(f"Error: {e}")

        # 4. Lanzamiento del juego
        self.ejecutar_juego()

    def ejecutar_juego(self):
        if os.path.exists(EJECUTABLE_PATH):
            self.label_detalles.configure(text="Abriendo proceso...")
            # Popen inicia el juego sin bloquear el launcher
            subprocess.Popen([EJECUTABLE_PATH], cwd=RUTA_CARPETA)
            self.after(2000, self.destroy) # Cierra el launcher tras 2 segundos
        else:
            self.label_estado.configure(text="Error fatal", text_color="red")
            self.label_detalles.configure(text="No se pudo encontrar Snake.exe")

if __name__ == "__main__":
    app = SnakeLauncher()
    app.mainloop()