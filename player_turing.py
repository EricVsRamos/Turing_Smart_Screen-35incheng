import os
import sys
import time
from glob import glob
from PIL import Image, ImageOps

# Adicionar biblioteca do Turing no path
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
if REPO_PATH not in sys.path:
    sys.path.insert(0, REPO_PATH)

from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation

COM_PORT = "COM3"
WIDTH, HEIGHT = 320, 480
SCREEN_W, SCREEN_H = 480, 320

def get_latest_gif():
    gifs_dir = r"c:\Users\thard\Downloads\GIFS"
    files = glob(os.path.join(gifs_dir, "*.gif"))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo .gif encontrado em {gifs_dir}")
    return files[0]

def prepare_gif_frames(gif_path, anim_w=240, anim_h=160):
    """
    Prepara os frames do GIF em uma resolução otimizada para o display.
    anim_w e anim_h definem a área do GIF.
    Se anim_w=480 e anim_h=320, é tela cheia.
    Se for menor (ex: 240x160), desenha no centro muito mais rápido!
    """
    print(f"Carregando GIF: {gif_path} (Tamanho do quadro: {anim_w}x{anim_h})")
    im = Image.open(gif_path)
    frames = []
    delays = []

    # Posicionar a animação no centro da tela
    pos_x = (SCREEN_W - anim_w) // 2
    pos_y = (SCREEN_H - anim_h) // 2

    # Pular frames se o GIF tiver muitos (ex: a cada 2 frames) para acelerar a fluidez
    frame_step = 2 if getattr(im, 'n_frames', 1) > 20 else 1

    frame_idx = 0
    try:
        while True:
            if frame_idx % frame_step == 0:
                frame = im.convert("RGBA")
                frame_resized = ImageOps.contain(frame, (anim_w, anim_h), method=Image.Resampling.BILINEAR)
                
                # Canvas do tamanho da animação
                canvas = Image.new("RGB", (anim_w, anim_h), (0, 0, 0))
                offset_x = (anim_w - frame_resized.width) // 2
                offset_y = (anim_h - frame_resized.height) // 2
                canvas.paste(frame_resized, (offset_x, offset_y))
                
                frames.append(canvas)
                
                duration = im.info.get("duration", 80) / 1000.0 * frame_step
                delays.append(max(0.04, duration))
            
            frame_idx += 1
            im.seek(im.tell() + 1)
    except EOFError:
        pass

    print(f"Total de {len(frames)} frames preparados para a regiao ({pos_x}, {pos_y})!")
    return frames, delays, pos_x, pos_y, anim_w, anim_h

def init_display(port=COM_PORT):
    try:
        print(f"Conectando a tela na porta {port}...")
        lcd = LcdCommRevA(com_port=port, display_width=WIDTH, display_height=HEIGHT)
        lcd.Reset()
        lcd.InitializeComm()
        lcd.SetBrightness(level=50)
        # REVERSE_LANDSCAPE para desvirar a imagem
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        print("Tela inicializada e invertida corretamente (REVERSE_LANDSCAPE)!")
        return lcd
    except Exception as e:
        print(f"Erro ao inicializar display: {e}")
        return None

def main():
    # TESTE RÁPIDO: tamanho 240x160 (4x menos dados que a tela cheia, atualiza muito mais rápido)
    anim_w = 260
    anim_h = 180
    
    gif_path = get_latest_gif()
    frames, delays, pos_x, pos_y, w, h = prepare_gif_frames(gif_path, anim_w=anim_w, anim_h=anim_h)
    
    lcd = init_display()
    if not lcd:
        return

    # Limpar a tela com fundo preto uma vez
    print("Limpando a tela...")
    bg = Image.new("RGB", (SCREEN_W, SCREEN_H), (10, 10, 15))
    lcd.DisplayPILImage(bg, 0, 0)

    print(f"\nIniciando reproducao na regiao central [{pos_x}, {pos_y}, {w}x{h}]...")
    print("Pressione Ctrl+C para parar.")

    try:
        while True:
            for frame, delay in zip(frames, delays):
                t0 = time.perf_counter()
                # Atualiza SOMENTE o retângulo da animação!
                lcd.DisplayPILImage(frame, pos_x, pos_y, w, h)
                elapsed = time.perf_counter() - t0
                sleep_time = max(0.01, delay - elapsed)
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        print("\nParado pelo usuario.")

if __name__ == "__main__":
    main()
