# Turing Smart Screen 3.5" - Desk Gallery & Relógio 🖥️✨

Aplicativo em Python com interface moderna (tema escuro estilo Windows 11) e suporte a bandeja do sistema (System Tray) para a tela secundária USB **Turing Smart Screen 3.5 polegadas** (revisão A / USB Monitor 3.5).

---

## 🚀 Funcionalidades

- **🌐 Modo Internet (Wallhaven Anime HD)**:
  - Busca e renderiza wallpapers aleatórios de animes em alta definição diretamente da API do Wallhaven.
  - Pré-carregamento em background para transições suaves sem travar a interface.

- **📁 Modo Galeria Local**:
  - Exibe imagens (PNG, JPG, JPEG, WebP) colocadas dentro da pasta `ARTES`.

- **🕒 Relógio & Calendário Integrado**:
  - Exibe horário, dia da semana e data em um badge com cantos arredondados e fundo translúcido no canto inferior da tela.
  - Atualização inteligente otimizada (atualiza apenas a região do badge a cada minuto).

- **🎛️ Painel de Controle Moderno**:
  - Interface com tema escuro elegante (`sv-ttk`).
  - Ajuste de intervalo de troca de imagens (5s, 10s, 15s, 30s, 60s).
  - Opção para pausar/retomar a qualquer momento.
  - Ativar ou desativar o relógio.

- **🔽 Execução em Segundo Plano (System Tray)**:
  - Botão de minimizar que oculta a janela e envia o programa para a bandeja do sistema (perto do relógio do Windows).
  - Menu de contexto na bandeja para reabrir o painel, pausar ou encerrar a aplicação.

---

## 📂 Estrutura do Projeto

```text
├── app.py                      # Aplicação principal (GUI Tkinter + Lógica do Display)
├── library/                    # Biblioteca de comunicação e drivers da tela Turing
├── ARTES/                      # Pasta para suas imagens e papéis de parede locais
├── galeria_anime_online.py     # Script independente de galeria anime com relógio
├── player_turing.py            # Script independente para exibição de imagens/GIFs
├── Iniciar_Turing_Gallery.bat  # Atalho para iniciar sem abrir janela de prompt
├── build_exe.bat               # Script para compilar o executável com PyInstaller
├── requirements.txt            # Dependências Python do projeto
├── COMO_USAR.txt               # Instruções rápidas em português
└── TuringGallery.exe           # Executável portátil compilado pronto para uso
```

---

## 🛠️ Instalação e Requisitos

### 1. Pré-requisitos
- **Python 3.10 ou superior** instalado no Windows.
- Tela Turing Smart Screen 3.5" conectada via cabo USB (porta COM identificada, por padrão `COM3`).

### 2. Instalar dependências

Abra o terminal (PowerShell ou CMD) na pasta do projeto e execute:

```bash
pip install -r requirements.txt
```

---

## ▶️ Como Usar

### Opção 1: Executável Pronto
- Basta dar dois cliques em **`TuringGallery.exe`**.

### Opção 2: Pelo Python
```bash
python app.py
```

### Opção 3: Em Segundo Plano (Sem Prompt)
- Dê dois cliques em **`Iniciar_Turing_Gallery.bat`**.

---

## 📦 Como Gerar o Executável (.exe)

Para gerar uma nova versão compilada portátil do executável para distribuição:

Dê dois cliques no arquivo **`build_exe.bat`** ou execute manualmente no terminal:

```bash
pyinstaller --noconsole --onefile --name "TuringGallery" --add-data "library;library" --collect-all sv_ttk --collect-all pystray app.py
```

O arquivo final será gerado em `dist/TuringGallery.exe`.

---

## ⚙️ Configuração da Porta COM

Caso sua tela conecte em outra porta COM que não seja `COM3`, você pode alterar a constante no topo do arquivo [`app.py`](app.py):

```python
COM_PORT = "COM3"  # Altere para COM4, COM5, etc.
```

---

## 📄 Licença
Código base da comunicação com o display sob licença GPL-3.0.
