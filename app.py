import os
import sys
import time
import json
import random
import glob
import urllib.request
import io
import datetime
import threading
from queue import Queue, Empty

import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
from PIL import Image, ImageDraw, ImageFont, ImageOps
import pystray
from pystray import MenuItem as item

# Garantir imports da biblioteca interna
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation

COM_PORT = "COM3"
WIDTH, HEIGHT = 320, 480
SCREEN_W, SCREEN_H = 480, 320

# Pasta das artes locais (relativa ao executável ou script)
if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(sys.executable)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))

ARTES_DIR = os.path.join(EXE_DIR, "ARTES")
os.makedirs(ARTES_DIR, exist_ok=True)

# Badge do Relógio
BADGE_W, BADGE_H = 136, 62
MARGIN = 10
BX0 = SCREEN_W - MARGIN - BADGE_W
BY0 = SCREEN_H - MARGIN - BADGE_H
BX1 = BX0 + BADGE_W
BY1 = BY0 + BADGE_H

DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Fontes
try:
    font_time = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)
    font_date = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 13)
except Exception:
    font_time = ImageFont.load_default()
    font_date = ImageFont.load_default()

def create_tray_icon_image():
    """Gera um ícone bonitinho para a bandeja do sistema."""
    icon_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon_img)
    d.rounded_rectangle([4, 4, 60, 60], radius=14, fill=(30, 144, 255))
    d.rectangle([14, 18, 50, 46], fill=(255, 255, 255))
    d.polygon([(26, 26), (38, 26), (32, 38)], fill=(30, 144, 255))
    return icon_img

class TuringGalleryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Turing 3.5\" - Galeria & Relógio")
        self.root.geometry("450x480")
        self.root.resizable(False, False)

        # Configurações do usuário
        self.running = True
        self.is_paused = False
        self.mode_var = tk.StringVar(value="internet")  # "internet" ou "local"
        self.interval_var = tk.IntVar(value=10)         # 10 segundos padrão!
        self.show_clock_var = tk.BooleanVar(value=True)

        self.lcd = None
        self.current_base = None
        self.last_minute = -1
        self.image_queue = Queue(maxsize=3)
        self.local_images = []
        self.url_pool = []

        # Configurar interface visual (Tema Escuro Windows 11)
        sv_ttk.set_theme("dark")
        self.build_ui()

        # Iniciar conexão com a tela em background
        threading.Thread(target=self.init_display_worker, daemon=True).start()

        # Iniciar thread do ciclo de exibição
        threading.Thread(target=self.display_loop_worker, daemon=True).start()

        # Iniciar thread de pre-fetch de imagens da internet
        threading.Thread(target=self.internet_fetcher_worker, daemon=True).start()

        # Configurar bandeja do sistema
        self.tray_icon = None
        self.setup_tray_icon()

        # Interceptar fechamento da janela para minimizar
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def build_ui(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Título
        title_lbl = ttk.Label(container, text="Turing 3.5\" Desk Gallery", font=("Segoe UI", 16, "bold"))
        title_lbl.pack(anchor="w", pady=(0, 5))

        # Status do display
        self.status_lbl = ttk.Label(container, text="Conectando à tela COM3...", font=("Segoe UI", 9))
        self.status_lbl.pack(anchor="w", pady=(0, 15))

        # Grupo: Modo de Exibição
        mode_frame = ttk.LabelFrame(container, text="Origem das Imagens", padding=12)
        mode_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Radiobutton(mode_frame, text="🌐 Internet (Anime Aleatório • Wallhaven HD)", 
                        variable=self.mode_var, value="internet").pack(anchor="w", pady=4)
        ttk.Radiobutton(mode_frame, text="📁 Galeria Local (Pasta Downloads\\ARTES)", 
                        variable=self.mode_var, value="local").pack(anchor="w", pady=4)

        # Grupo: Configurações
        config_frame = ttk.LabelFrame(container, text="Configurações", padding=12)
        config_frame.pack(fill=tk.X, pady=(0, 15))

        row1 = ttk.Frame(config_frame)
        row1.pack(fill=tk.X, pady=4)
        ttk.Label(row1, text="Tempo de troca:").pack(side=tk.LEFT)
        
        interval_combo = ttk.Combobox(row1, values=["5 segundos", "10 segundos", "15 segundos", "30 segundos", "60 segundos"], 
                                      state="readonly", width=14)
        interval_combo.set("10 segundos")
        interval_combo.pack(side=tk.RIGHT)
        interval_combo.bind("<<ComboboxSelected>>", lambda e: self.on_interval_change(interval_combo.get()))

        ttk.Checkbutton(config_frame, text="Exibir Relógio no canto inferior", 
                        variable=self.show_clock_var).pack(anchor="w", pady=(6, 2))

        # Botões de Ação
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_pause = ttk.Button(btn_frame, text="⏸ Pausar", command=self.toggle_pause)
        self.btn_pause.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        btn_folder = ttk.Button(btn_frame, text="📁 Abrir Pasta ARTES", command=self.open_artes_folder)
        btn_folder.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

        # Botão minimizar
        btn_min = ttk.Button(container, text="🔽 Minimizar para Segundo Plano", style="Accent.TButton", 
                             command=self.minimize_to_tray)
        btn_min.pack(fill=tk.X, pady=(10, 0))

    def on_interval_change(self, text):
        seconds = int(text.split()[0])
        self.interval_var.set(seconds)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.config(text="▶ Retomar")
        else:
            self.btn_pause.config(text="⏸ Pausar")

    def open_artes_folder(self):
        os.startfile(ARTES_DIR)

    def setup_tray_icon(self):
        menu = (
            item('Abrir Painel', self.restore_from_tray, default=True),
            item('Pausar / Retomar', self.toggle_pause),
            item('Sair', self.quit_app)
        )
        self.tray_icon = pystray.Icon("TuringGallery", create_tray_icon_image(), "Turing 3.5\" Gallery", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def minimize_to_tray(self):
        self.root.withdraw()

    def restore_from_tray(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon=None, item=None):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def init_display_worker(self):
        try:
            lcd = LcdCommRevA(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
            lcd.Reset()
            lcd.InitializeComm()
            lcd.SetBrightness(level=55)
            lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
            self.lcd = lcd
            self.root.after(0, lambda: self.status_lbl.config(text="🟢 Conectado na porta COM3 (Ativo)", foreground="#4cd964"))
        except Exception as e:
            self.root.after(0, lambda: self.status_lbl.config(text=f"🔴 Erro de conexão: {e}", foreground="#ff3b30"))

    def internet_fetcher_worker(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        while self.running:
            if self.mode_var.get() == "internet" and self.image_queue.qsize() < 2:
                if not self.url_pool:
                    try:
                        url_api = "https://wallhaven.cc/api/v1/search?categories=010&purity=100&ratios=16x9,16x10&sorting=random"
                        req = urllib.request.Request(url_api, headers=headers)
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            self.url_pool = [i["path"] for i in data.get("data", []) if "path" in i]
                    except Exception:
                        time.sleep(5)
                        continue

                if self.url_pool:
                    next_url = self.url_pool.pop(0)
                    try:
                        req = urllib.request.Request(next_url, headers=headers)
                        with urllib.request.urlopen(req, timeout=12) as resp:
                            im = Image.open(io.BytesIO(resp.read())).convert("RGB")
                            fitted = ImageOps.fit(im, (SCREEN_W, SCREEN_H), method=Image.Resampling.LANCZOS)
                            self.image_queue.put(fitted)
                    except Exception:
                        pass
            time.sleep(1)

    def get_next_local_image(self):
        files = glob.glob(os.path.join(ARTES_DIR, "*.*"))
        valid = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if not valid:
            return None
        chosen = random.choice(valid)
        try:
            im = Image.open(chosen).convert("RGB")
            return ImageOps.fit(im, (SCREEN_W, SCREEN_H), method=Image.Resampling.LANCZOS)
        except Exception:
            return None

    def compose_frame(self, base_image):
        canvas = base_image.copy()
        now = datetime.datetime.now()

        if self.show_clock_var.get():
            overlay = Image.new("RGBA", (SCREEN_W, SCREEN_H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            time_str = now.strftime("%H:%M")
            dia = DIAS[now.weekday()]
            mes = MESES[now.month - 1]
            date_str = f"{dia}, {now.day:02d} {mes}"

            draw.rounded_rectangle([BX0, BY0, BX1, BY1], radius=12, fill=(0, 0, 0, 160))
            draw.text((BX0 + 16, BY0 + 4), time_str, font=font_time, fill=(255, 255, 255, 255))
            draw.text((BX0 + 16, BY0 + 43), date_str, font=font_date, fill=(190, 215, 255, 240))

            canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

        return canvas, now.minute

    def display_loop_worker(self):
        last_switch = 0
        while self.running:
            if not self.lcd or self.is_paused:
                time.sleep(0.5)
                continue

            now = datetime.datetime.now()
            interval = self.interval_var.get()

            # Momento de trocar de imagem
            if time.time() - last_switch >= interval or self.current_base is None:
                next_img = None
                if self.mode_var.get() == "internet":
                    try:
                        next_img = self.image_queue.get_nowait()
                    except Empty:
                        pass
                else:
                    next_img = self.get_next_local_image()

                if next_img is not None:
                    self.current_base = next_img
                    frame, self.last_minute = self.compose_frame(self.current_base)
                    try:
                        self.lcd.DisplayPILImage(frame, 0, 0)
                        last_switch = time.time()
                    except Exception as e:
                        print(f"Erro ao desenhar imagem: {e}")

            # Atualização instantânea somente do relógio ao virar o minuto
            elif self.show_clock_var.get() and now.minute != self.last_minute and self.current_base is not None:
                frame, self.last_minute = self.compose_frame(self.current_base)
                clock_crop = frame.crop((BX0, BY0, BX1, BY1))
                try:
                    self.lcd.DisplayPILImage(clock_crop, BX0, BY0, BADGE_W, BADGE_H)
                except Exception:
                    pass

            time.sleep(0.5)

if __name__ == "__main__":
    root = tk.Tk()
    app = TuringGalleryApp(root)
    root.mainloop()
