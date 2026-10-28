"""Tema visual: vidro fosco claro e quente (referência: Tangerine).

Toda cor, medida e duração da interface mora aqui. Cores são tuplas RGB(A)
de 0 a 1 para o cairo; a versão em hex fica no comentário e no CSS.
"""
from __future__ import annotations


def _hex(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255,
            int(h[4:6], 16) / 255, a)


def rgba255(r: int, g: int, b: int, a: float) -> tuple[float, ...]:
    return (r / 255, g / 255, b / 255, a)


# --------------------------------------------------------------------------
# Paleta
# --------------------------------------------------------------------------
ORANGE = "#FF5A1F"                 # ação primária, hover, alças
ORANGE_DEEP = "#FD4D02"            # fim do gradiente de hover
ORANGE_RING = "#F79241"            # anel do miolo
ORANGE_PILL = "#FDC375"            # pílula do miolo
TEXT = "#3A2A20"                   # texto em repouso (marrom quase preto)
TEXT_SOFT = "#8A4A10"              # miolo, botões planos, opções inativas
WHITE = "#FFFFFF"
WINDOW_TOP = "#FFB45A"             # gradiente das janelas
WINDOW_BOTTOM = "#FF8A4C"
WINDOW_ALPHA = 0.92

# --------------------------------------------------------------------------
# Roda (medidas em função de R, o raio externo)
# --------------------------------------------------------------------------
WHEEL_R = 150.0
SECTOR_IN = 0.42                   # faixa dos setores: 0,42R a 0,92R
SECTOR_OUT = 0.92
OUTER_IN = 0.98                    # 2º anel (mais de 10 itens)
OUTER_OUT = 1.44
RIM_PAD = 0.08                     # aro além do último anel
CORE_RING_IN = 0.30                # anel laranja do miolo
CORE_RING_OUT = 0.40
CORE_PILL_W = 0.62
CORE_PILL_H = 0.24
RING_CAPACITY = (10, 16)
SECTOR_GAP = 6.0                   # px, constante ao longo do arco
SECTOR_CORNER = 13.0               # px, cantos das pílulas anelares
HOVER_GROW = 0.02                  # setor em hover cresce 2% para fora
SLOP = 48.0                        # tolerância além do aro que ainda seleciona
EDGE_MARGIN = 12.0                 # distância mínima da borda da tela

RIM_FILL = rgba255(255, 246, 236, 0.35)     # branco quente ~35%
RIM_STROKE = rgba255(255, 255, 255, 0.60)
RIM_STROKE_W = 1.5
CORE_RING = _hex(ORANGE_RING, 0.70)
CORE_PILL = _hex(ORANGE_PILL)
SECTOR_TOP = rgba255(255, 242, 232, 0.70)   # repouso: mais claro no topo
SECTOR_BOTTOM = rgba255(255, 232, 214, 0.56)
SECTOR_EDGE = rgba255(255, 255, 255, 0.55)
HOVER_TOP = _hex(ORANGE)
HOVER_BOTTOM = _hex(ORANGE_DEEP)
SHADOW = rgba255(120, 40, 0, 0.18)
SHADOW_BLUR = 24.0
SHADOW_DY = 6.0

LABEL_COLOR = _hex(TEXT)
LABEL_HOVER = _hex(WHITE)
LABEL_PX = 11.0
LABEL_MIN_PX = 8.0                 # encolhe até aqui antes de quebrar linha
LABEL_WEIGHT = 700
LABEL_TRACKING = 0.5               # px
CORE_COLOR = _hex(TEXT_SOFT)
CORE_PX = 10.0
CORE_WEIGHT = 600
ICON_PX = 16.0
ICON_GAP = 3.0
ICON_STROKE = 1.5
FONT_FAMILY = "Inter, Cantarell, Sans"

# Movimento (ms)
ENTER_MS = 140
ENTER_SCALE = 0.92
HOVER_MS = 80
MODE_FADE_MS = 120

# --------------------------------------------------------------------------
# Rótulos e ícones da roda (os ids das operações não mudam)
# --------------------------------------------------------------------------
LABELS = {
    # ferramentas
    "img-edit": "EDIT", "img-crop": "CROP", "img-size": "RESIZE",
    "img-addbg": "ADD BG", "img-rmbg": "REMOVE BG",
    "img-compress": "COMPRESS", "img-rotate": "ROTATE",
    "img-qr": "READ QR", "img-pdf": "TO PDF", "img-collage": "COLLAGE",
    "vid-trim": "TRIM", "vid-size": "RESIZE", "vid-compress": "COMPRESS",
    "vid-mute": "MUTE", "vid-2x": "2× SPEED", "vid-rotate": "ROTATE",
    "vid-snap": "SNAPSHOT", "vid-join": "JOIN",
    "aud-trim": "TRIM", "aud-normalize": "NORMALIZE",
    "aud-compress": "COMPRESS", "aud-mono": "MONO", "aud-silence": "SILENCE",
    "aud-join": "JOIN",
    "pdf-pages": "PAGES", "pdf-compress": "COMPRESS", "pdf-split": "SPLIT",
    "pdf-rotate": "ROTATE", "pdf-images": "IMAGES", "pdf-merge": "MERGE",
    "strip-meta": "STRIP META", "show-meta": "METADATA",
    # ações
    "act-copy-path": "COPY PATH", "act-terminal": "TERMINAL",
    "act-copy-to": "COPY TO", "act-move-to": "MOVE TO", "act-float": "FLOAT",
    "act-zip-all": "ZIP",
    # conversão (o resto já é o nome do formato)
    "extract": "EXTRACT",
}

ICONS = {
    "img-edit": "sliders", "img-crop": "crop", "img-size": "resize",
    "img-addbg": "image", "img-rmbg": "eraser",
    "img-compress": "compress", "img-rotate": "rotate",
    "img-qr": "qr", "img-pdf": "doc", "img-collage": "grid",
    "vid-trim": "scissors", "vid-size": "resize", "vid-compress": "compress",
    "vid-mute": "mute", "vid-2x": "speed", "vid-rotate": "rotate",
    "vid-snap": "camera", "vid-join": "merge",
    "aud-trim": "scissors", "aud-normalize": "wave", "aud-compress": "compress",
    "aud-mono": "wave", "aud-silence": "wave", "aud-join": "merge",
    "pdf-pages": "pages", "pdf-compress": "compress", "pdf-split": "split",
    "pdf-rotate": "rotate", "pdf-images": "image", "pdf-merge": "merge",
    "strip-meta": "eye-off", "show-meta": "tag",
    "act-copy-path": "link", "act-terminal": "terminal",
    "act-copy-to": "copy", "act-move-to": "move", "act-float": "pin",
    "act-zip-all": "archive",
}


def wheel_label(op) -> str:
    return LABELS.get(op.id, op.label).upper()


def wheel_icon(op) -> str | None:
    """Ícone de linha; a roda de conversão não usa ícones."""
    return ICONS.get(op.id) if op.group != "convert" else None


def human_size(n: int) -> str:
    """Tamanho como no Finder (base 1000): 1.1 MB."""
    if n < 1000:
        return f"{n} B"
    for unit in ("KB", "MB", "GB", "TB"):
        n /= 1000
        if n < 1000 or unit == "TB":
            return f"{n:.1f} {unit}" if n < 100 else f"{n:.0f} {unit}"
    return ""


# --------------------------------------------------------------------------
# Janelas de edição
# --------------------------------------------------------------------------
WINDOW_RADIUS = 16
HANDLE_PX = 8                      # alças quadradas do recorte
CROP_DIM = rgba255(60, 60, 60, 0.55)
CROP_LINE = rgba255(255, 255, 255, 0.95)
HANDLE = _hex(ORANGE)
SWATCH_PX = 22
SWATCH_RADIUS = 6

# Add BG: 9 gradientes (quentes e frios) e 9 sólidas
BG_GRADIENTS: list[tuple[str, str]] = [
    ("#FF9A5A", "#FF4E50"), ("#F6D365", "#FDA085"), ("#FBC2EB", "#A6C1EE"),
    ("#FF7EB3", "#FF758C"), ("#F093FB", "#F5576C"), ("#4FACFE", "#00F2FE"),
    ("#43E97B", "#38F9D7"), ("#667EEA", "#764BA2"), ("#30CFD0", "#330867"),
]
BG_SOLIDS: list[str] = [
    "#FFFFFF", "#FFD60A", "#C6F432", "#34C759", "#30B0A7", "#32ADE6",
    "#0A84FF", "#1C2C5B", "#AF52DE",
]
BG_PADDING = (0, 1000, 100)        # min, max, padrão (px da imagem)
BG_CORNERS = (0, 300, 104)
BG_SHADOW = (0, 100, 24)
BG_RATIOS: list[tuple[str, float | None]] = [
    ("Auto", None), ("1:1", 1.0), ("16:9", 16 / 9), ("4:5", 4 / 5),
]

CSS = """
/* ---------- janelas de edição: vidro laranja ---------- */
window.mx-window {
  background: linear-gradient(180deg,
      alpha(%(top)s, %(alpha)s), alpha(%(bottom)s, %(alpha)s));
  border-radius: %(radius)dpx;
  color: %(text)s;
  border: 1px solid alpha(white, 0.45);
}
window.mx-window > * { border-radius: %(radius)dpx; }
.mx-header { padding: 10px 12px 4px 12px; }
.mx-title { font-weight: 600; font-size: 13px; color: %(text)s; }
button.mx-close {
  min-width: 22px; min-height: 22px; padding: 0; border-radius: 999px;
  background: alpha(white, 0.45); color: %(soft)s; border: none;
  box-shadow: none; font-weight: 700;
}
button.mx-close:hover { background: alpha(white, 0.70); }
.mx-footer { padding: 6px 14px 14px 14px; }
button.mx-flat {
  background: none; border: none; box-shadow: none; color: %(soft)s;
  font-weight: 600; padding: 6px 10px;
}
button.mx-flat:hover { background: alpha(white, 0.30); border-radius: 999px; }
button.mx-primary {
  background: %(orange)s; color: white; font-weight: 600; border: none;
  border-radius: 999px; padding: 6px 18px; box-shadow: 0 2px 6px alpha(#7a2800, 0.25);
}
button.mx-primary:hover { background: #ff6c36; }
button.mx-primary:disabled { background: alpha(%(orange)s, 0.45); color: alpha(white, 0.8); }
.mx-label { color: %(text)s; font-weight: 600; font-size: 12px; }
.mx-dim { color: %(soft)s; font-size: 11px; }
.mx-value { color: %(soft)s; font-size: 11px; font-feature-settings: "tnum"; min-width: 48px; }
.mx-error { color: #9b1c00; font-size: 11px; font-weight: 600; }

/* controles segmentados em pílula */
.mx-segmented { background: alpha(white, 0.22); border-radius: 999px; padding: 2px; }
window.mx-window .mx-segmented button {
  background: alpha(white, 0.35); color: %(soft)s; border: none; box-shadow: none;
  border-radius: 999px; padding: 3px 10px; margin: 1px; font-weight: 600;
  font-size: 11px; min-height: 0;
}
window.mx-window .mx-segmented button:checked { background: %(orange)s; color: white; }

/* campos, listas, sliders */
window.mx-window entry, window.mx-window spinbutton, window.mx-window dropdown > button {
  background: alpha(white, 0.45); color: %(text)s; border: none; box-shadow: none;
  border-radius: 8px; min-height: 26px;
}
window.mx-window button {
  background: alpha(white, 0.35); color: %(text)s; border: none; box-shadow: none;
  border-radius: 8px;
}
window.mx-window button:hover { background: alpha(white, 0.55); }
window.mx-window button.mx-primary { background: %(orange)s; color: white; }
window.mx-window button.mx-primary:hover { background: #ff6c36; }
window.mx-window button.mx-flat { background: none; }
window.mx-window button.mx-close { background: alpha(white, 0.45); }
window.mx-window scale trough { background: alpha(white, 0.40); min-height: 4px; border-radius: 99px; }
window.mx-window scale highlight { background: %(orange)s; border-radius: 99px; }
window.mx-window scale slider {
  background: white; min-width: 16px; min-height: 16px; margin: -6px; border-radius: 99px;
  box-shadow: 0 1px 3px alpha(#7a2800, 0.35); border: none;
}
window.mx-window checkbutton check, window.mx-window switch {
  background: alpha(white, 0.45); border: none;
}
window.mx-window checkbutton check:checked, window.mx-window switch:checked {
  background: %(orange)s; color: white;
}
window.mx-window switch slider { background: white; }
window.mx-window scrolledwindow, window.mx-window viewport, window.mx-window flowbox {
  background: none;
}
.mx-canvas { background: alpha(white, 0.18); border-radius: 12px; }
.mx-frame { background: alpha(#3a2a20, 0.12); border-radius: 10px; }

/* Add BG */
window.mx-window button.mx-swatch {
  min-width: %(sw)dpx; min-height: %(sw)dpx; padding: 0; border-radius: %(swr)dpx;
  border: 2px solid transparent; box-shadow: inset 0 0 0 1px alpha(black, 0.08);
}
window.mx-window button.mx-swatch.selected { border-color: white; box-shadow: 0 0 0 1px alpha(%(orange)s, 0.6); }
button.mx-pill { border-radius: 999px; padding: 2px 10px; font-size: 11px; font-weight: 600; }

/* janela Flutuar (com barra do sistema) */
window.mx-window headerbar { background: none; box-shadow: none; border: none; color: %(text)s; }

/* páginas do PDF */
window.mx-window button.mx-page { padding: 6px; border-radius: 10px; background: alpha(white, 0.30); border: 2px solid transparent; }
window.mx-window button.mx-page:checked { background: alpha(white, 0.55); border-color: %(orange)s; }
""" % {
    "top": WINDOW_TOP, "bottom": WINDOW_BOTTOM, "alpha": WINDOW_ALPHA,
    "radius": WINDOW_RADIUS, "text": TEXT, "soft": TEXT_SOFT,
    "orange": ORANGE, "sw": SWATCH_PX, "swr": SWATCH_RADIUS,
}
