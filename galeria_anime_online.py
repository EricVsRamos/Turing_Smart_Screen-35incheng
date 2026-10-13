import os
import sys
import time
import json
import urllib.request
import io
import datetime
import threading
from queue import Queue, Empty
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Adicionar biblioteca do Turing no path
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
if REPO_PATH not in sys.path:
    sys.path.insert(0, REPO_PATH)

from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation

COM_PORT = "COM3"
WIDTH, HEIGHT = 320, 480
SCREEN_W, SCREEN_H = 480, 320

# Intervalo entre as trocas de wallpaper (em segundos)
WALLPAPER_INTERVAL = 25

# Badge do Relógio (posicionado no canto inferior direito)
BADGE_W, BADGE_H = 136, 62
MARGIN = 10
BX0 = SCREEN_W - MARGIN - BADGE_W
BY0 = SCREEN_H - MARGIN - BADGE_H
BX1 = BX0 + BADGE_W
BY1 = BY0 + BADGE_H

DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Fontes do Windows
FONT_PATH_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_PATH_REG = r"C:\Windows\Fonts\segoeui.ttf"

try:
    font_time = ImageFont.truetype(FONT_PATH_BOLD, 36)
    font_date = ImageFont.truetype(FONT_PATH_REG, 13)
except Exception:
    font_time = ImageFont.load_default()
    font_date = ImageFont.load_default()

def fetch_wallhaven_urls():
    """Busca uma lista de URLs de wallpapers de anime aleatórios em alta definição no Wallhaven."""
    url_api = "https://wallhaven.cc/api/v1/search?categories=010&purity=100&ratios=16x9,16x10&sorting=random"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        req = urllib.request.Request(url_api, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            urls = [item["path"] for item in data.get("data", []) if "path" in item]
            print(f"[API] Recebida lista com {len(urls)} wallpapers de anime!")
            return urls
    except Exception as e:
        print(f"[API] Erro ao consultar Wallhaven: {e}")
        return []

def download_and_process_image(img_url):
    """Baixa a imagem diretamente para a memória e ajusta perfeitamente para 480x320."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(img_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_bytes = resp.read()
        
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        # Ajusta e centraliza proporcionalmente para preencher os 480x320 sem bordas pretas
        fitted = ImageOps.fit(im, (SCREEN_W, SCREEN_H), method=Image.Resampling.LANCZOS)
        return fitted
    except Exception as e:
        print(f"[Download] Erro ao baixar imagem {img_url}: {e}")
        return None

def compose_image_with_clock(base_image):
    """Desenha o badge do relógio translúcido sobre a imagem base."""
    canvas = base_image.copy()
    overlay = Image.new("RGBA", (SCREEN_W, SCREEN_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M")
    dia_semana = DIAS[now.weekday()]
    mes_str = MESES[now.month - 1]
    date_str = f"{dia_semana}, {now.day:02d} {mes_str}"

    # Fundo arredondado translúcido estilo 'glassmorphism'
    draw.rounded_rectangle([BX0, BY0, BX1, BY1], radius=12, fill=(0, 0, 0, 160))
    
    # Texto das horas
    draw.text((BX0 + 16, BY0 + 4), time_str, font=font_time, fill=(255, 255, 255, 255))
    # Texto da data
    draw.text((BX0 + 16, BY0 + 43), date_str, font=font_date, fill=(190, 215, 255, 240))

    final = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    return final, now.minute

class ImageFetcherThread(threading.Thread):
    """Thread em segundo plano que mantém a próxima imagem já baixada e pronta na memória."""
    def __init__(self, queue_out):
        super().__init__(daemon=True)
        self.queue_out = queue_out
        self.url_pool = []

    def run(self):
        while True:
            if self.queue_out.qsize() < 2:
                if not self.url_pool:
                    self.url_pool = fetch_wallhaven_urls()
                    if not self.url_pool:
                        time.sleep(5)
                        continue
                
                next_url = self.url_pool.pop(0)
                img = download_and_process_image(next_url)
                if img:
                    self.queue_out.put(img)
            time.sleep(1)

def init_display(port=COM_PORT):
    try:
        print(f"Conectando na telinha ({port})...")
        lcd = LcdCommRevA(com_port=port, display_width=WIDTH, display_height=HEIGHT)
        lcd.Reset()
        lcd.InitializeComm()
        lcd.SetBrightness(level=55)
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        print("Telinha conectada e pronta!")
        return lcd
    except Exception as e:
        print(f"Erro ao conectar com a tela: {e}")
        return None

def main():
    lcd = init_display()
    if not lcd:
        print("Certifique-se de que nenhum outro programa está usando a porta COM3.")
        return

    # Iniciar download em segundo plano
    image_queue = Queue(maxsize=3)
    fetcher = ImageFetcherThread(image_queue)
    fetcher.start()

    print("\nAguardando download da primeira arte...")
    while image_queue.empty():
        time.sleep(0.5)

    current_base = image_queue.get()
    full_image, last_minute = compose_image_with_clock(current_base)
    
    print("Exibindo primeira arte na tela!")
    lcd.DisplayPILImage(full_image, 0, 0)
    last_switch_time = time.time()

    print(f"\n[Galeria Online Ativa] Trocando de arte a cada {WALLPAPER_INTERVAL}s. Pressione Ctrl+C para sair.\n")

    try:
        while True:
            now = datetime.datetime.now()

            # 1. Troca periódica de imagem
            if time.time() - last_switch_time >= WALLPAPER_INTERVAL:
                try:
                    next_base = image_queue.get_nowait()
                    current_base = next_base
                    full_image, last_minute = compose_image_with_clock(current_base)
                    print(f"[{now.strftime('%H:%M:%S')}] Atualizando com nova arte de anime da internet!")
                    lcd.DisplayPILImage(full_image, 0, 0)
                    last_switch_time = time.time()
                except Empty:
                    # Se ainda estiver baixando, espera o próximo ciclo
                    pass

            # 2. Atualização rápida somente do relógio a cada mudança de minuto
            elif now.minute != last_minute:
                full_image, last_minute = compose_image_with_clock(current_base)
                # Recorta apenas o retângulo do relógio
                clock_crop = full_image.crop((BX0, BY0, BX1, BY1))
                # Atualização relâmpago de ~15 milissegundos imperceptível
                lcd.DisplayPILImage(clock_crop, BX0, BY0, BADGE_W, BADGE_H)

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nGaleria interrompida pelo usuário.")

if __name__ == "__main__":
    main()
