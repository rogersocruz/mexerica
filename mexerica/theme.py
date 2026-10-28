"""Tema visual: vidro fosco claro e quente (referência: Tangerine).

Toda cor, medida e duração da interface mora aqui. Cores são tuplas RGB(A)
de 0 a 1 para o cairo; a versão em hex fica no comentário e no CSS.

As cores vêm de um estilo (STYLES); apply() troca o estilo, a opacidade
das janelas e as animações em tempo real (Configurações). Quem desenha lê
sempre TH.<NOME> na hora, então a troca vale no próximo quadro; o CSS é
refeito e o app o recarrega.
"""
from __future__ import annotations

import sys


def _hex(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255,
            int(h[4:6], 16) / 255, a)


def rgba255(r: int, g: int, b: int, a: float) -> tuple[float, ...]:
    return (r / 255, g / 255, b / 255, a)


# --------------------------------------------------------------------------
# Estilos (paletas). "mexerica" é o visual original.
# --------------------------------------------------------------------------
# accent: ação primária, hover, alças · deep: fim do gradiente de hover ·
# ring/pill: miolo · text: texto em repouso · soft: miolo, botões planos ·
# top/bottom: gradiente das janelas · sector_*/rim/edge/rim_stroke: vidro da
# roda · shadow: sombra da roda
STYLES: dict[str, dict] = {
    "mexerica": dict(
        name="Mexerica", accent="#FF5A1F", deep="#FD4D02", ring="#F79241",
        pill="#FDC375", text="#3A2A20", soft="#8A4A10", top="#FFB45A",
        bottom="#FF8A4C", sector_top=(255, 242, 232, 0.70),
        sector_bottom=(255, 232, 214, 0.56), rim=(255, 246, 236, 0.35),
        rim_stroke=(255, 255, 255, 0.60), edge=(255, 255, 255, 0.55),
        shadow=(120, 40, 0, 0.18)),
    "oceano": dict(
        name="Oceano", accent="#1E7BEA", deep="#1462C9", ring="#5AA2F0",
        pill="#A9D1FA", text="#14263A", soft="#1F4E7A", top="#8CC4FA",
        bottom="#5A9EF0", sector_top=(236, 245, 255, 0.72),
        sector_bottom=(222, 236, 252, 0.58), rim=(240, 247, 255, 0.35),
        rim_stroke=(255, 255, 255, 0.60), edge=(255, 255, 255, 0.55),
        shadow=(0, 40, 110, 0.18)),
    "menta": dict(
        name="Menta", accent="#13A06B", deep="#0E8657", ring="#4CC793",
        pill="#A6E8C9", text="#13302A", soft="#1E5E49", top="#8EE3BE",
        bottom="#4FC896", sector_top=(236, 252, 245, 0.72),
        sector_bottom=(220, 246, 234, 0.58), rim=(240, 252, 247, 0.35),
        rim_stroke=(255, 255, 255, 0.60), edge=(255, 255, 255, 0.55),
        shadow=(0, 90, 50, 0.18)),
    "uva": dict(
        name="Uva", accent="#8B4DFF", deep="#7433F0", ring="#AD82FF",
        pill="#D8C3FF", text="#271A3D", soft="#553089", top="#C3A4FF",
        bottom="#9F74FF", sector_top=(246, 240, 255, 0.72),
        sector_bottom=(236, 226, 255, 0.58), rim=(248, 244, 255, 0.35),
        rim_stroke=(255, 255, 255, 0.60), edge=(255, 255, 255, 0.55),
        shadow=(60, 0, 120, 0.18)),
    "grafite": dict(
        name="Grafite", accent="#FF7A3D", deep="#F05F1E", ring="#FF9A63",
        pill="#4A4A50", text="#F2F2F2", soft="#D2D2D8", top="#3C3C42",
        bottom="#26262B", sector_top=(62, 62, 68, 0.80),
        sector_bottom=(40, 40, 46, 0.74), rim=(28, 28, 32, 0.45),
        rim_stroke=(255, 255, 255, 0.22), edge=(255, 255, 255, 0.16),
        shadow=(0, 0, 0, 0.35)),
}
STYLE = "mexerica"
WHITE = "#FFFFFF"
# preenchidos por apply()
ORANGE = ORANGE_DEEP = ORANGE_RING = ORANGE_PILL = ""
TEXT = TEXT_SOFT = WINDOW_TOP = WINDOW_BOTTOM = ""
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

RIM_STROKE_W = 1.5
# cores da roda: apply() preenche a partir do estilo (repouso mais claro no
# topo, hover no acento)
RIM_FILL = RIM_STROKE = CORE_RING = CORE_PILL = SECTOR_TOP = ()
SECTOR_BOTTOM = SECTOR_EDGE = HOVER_TOP = HOVER_BOTTOM = SHADOW = ()
SHADOW_BLUR = 24.0
SHADOW_DY = 6.0

LABEL_COLOR = ()
LABEL_HOVER = _hex(WHITE)
LABEL_PX = 11.0
LABEL_MIN_PX = 8.0                 # encolhe até aqui antes de quebrar linha
LABEL_WEIGHT = 700
LABEL_TRACKING = 0.5               # px
CORE_COLOR = ()
CORE_PX = 10.0
CORE_WEIGHT = 600
ICON_PX = 16.0
ICON_GAP = 3.0
ICON_STROKE = 1.5
FONT_FAMILY = "Inter, Cantarell, Segoe UI, Sans"

# Movimento (ms); sem animações, apply() reduz a 1 ms
MOTION = {"ENTER_MS": 140, "HOVER_MS": 80, "MODE_FADE_MS": 120}
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
# No Windows 11 o DWM arredonda a janela com 8 px e o vidro (borrão) segue
# esse contorno, então o CSS usa o mesmo raio.
WINDOW_RADIUS = 8 if sys.platform == "win32" else 16
HANDLE_PX = 8                      # alças quadradas do recorte
CROP_DIM = rgba255(60, 60, 60, 0.55)
CROP_LINE = rgba255(255, 255, 255, 0.95)
HANDLE = ()                        # acento do estilo (apply)
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

_CSS = """
/* ---------- janelas de edição: vidro na cor do estilo ---------- */
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

/* janela Flutuar: redonda, desenhada pelo app (floating.py) */
window.mx-float, window.mx-float.background {
  background: none; box-shadow: none; border: none;
}
.mx-float-label {
  background: alpha(%(top)s, 0.95); color: %(text)s; border-radius: 999px;
  padding: 3px 10px; font-weight: 600; font-size: 11px;
  box-shadow: 0 1px 4px alpha(black, 0.18);
}
button.mx-float-close {
  min-width: 0; min-height: 0; padding: 0; border-radius: 999px;
  background: %(orange)s; color: white; font-weight: 700; font-size: 14px;
  border: 2px solid white; box-shadow: 0 1px 4px alpha(black, 0.25);
}
button.mx-float-close:hover { opacity: 0.88; }
.mx-float-badge {
  background: %(orange)s; color: white; border-radius: 999px;
  min-width: 18px; padding: 1px 5px; font-weight: 700; font-size: 11px;
  border: 2px solid white;
}

/* Configurações (settings_window.py): janela comum, acento do estilo */
.mx-settings .mx-page-title { font-size: 20px; font-weight: 700; }
.mx-settings .mx-section { font-weight: 700; font-size: 12px; opacity: 0.65;
  margin-top: 8px; }
.mx-settings .mx-hint { font-size: 12px; opacity: 0.7; }
.mx-settings button.mx-chip { border-radius: 999px; padding: 3px 12px;
  font-weight: 600; font-size: 12px; }
.mx-settings button.mx-chip:checked { background: %(orange)s; color: white; }
.mx-settings button.mx-chip.mx-missing { opacity: 0.5; }
.mx-settings button.mx-style { border-radius: 12px; padding: 6px 10px; }
.mx-settings button.mx-style:checked {
  box-shadow: inset 0 0 0 2px %(orange)s; background: alpha(%(orange)s, 0.08);
}
.mx-settings .mx-preview {
  border-radius: 14px;
  background: linear-gradient(135deg, #d6dde6, #8e9fb3 60%%, #5f6f84);
}
.mx-settings .mx-ok { color: #1b8a3a; font-weight: 700; }
.mx-settings .mx-key { color: %(orange)s; font-weight: 700; }
.mx-settings .mx-missing-mark { color: #b3261e; font-weight: 700; }

/* páginas do PDF */
window.mx-window button.mx-page { padding: 6px; border-radius: 10px; background: alpha(white, 0.30); border: 2px solid transparent; }
window.mx-window button.mx-page:checked { background: alpha(white, 0.55); border-color: %(orange)s; }
"""
CSS = ""


def apply(style: str = "mexerica", opacity: float = 0.92,
          animations: bool = True) -> None:
    """Troca o estilo, a opacidade das janelas e as animações."""
    global STYLE, ORANGE, ORANGE_DEEP, ORANGE_RING, ORANGE_PILL, TEXT
    global TEXT_SOFT, WINDOW_TOP, WINDOW_BOTTOM, WINDOW_ALPHA, RIM_FILL
    global RIM_STROKE, CORE_RING, CORE_PILL, SECTOR_TOP, SECTOR_BOTTOM
    global SECTOR_EDGE, HOVER_TOP, HOVER_BOTTOM, SHADOW, LABEL_COLOR
    global CORE_COLOR, HANDLE, CSS, ENTER_MS, HOVER_MS, MODE_FADE_MS
    if style not in STYLES:
        style = "mexerica"
    p = STYLES[style]
    STYLE = style
    ORANGE, ORANGE_DEEP = p["accent"], p["deep"]
    ORANGE_RING, ORANGE_PILL = p["ring"], p["pill"]
    TEXT, TEXT_SOFT = p["text"], p["soft"]
    WINDOW_TOP, WINDOW_BOTTOM = p["top"], p["bottom"]
    WINDOW_ALPHA = max(0.5, min(float(opacity), 1.0))
    RIM_FILL, RIM_STROKE = rgba255(*p["rim"]), rgba255(*p["rim_stroke"])
    SECTOR_TOP, SECTOR_BOTTOM = (rgba255(*p["sector_top"]),
                                 rgba255(*p["sector_bottom"]))
    SECTOR_EDGE, SHADOW = rgba255(*p["edge"]), rgba255(*p["shadow"])
    CORE_RING, CORE_PILL = _hex(ORANGE_RING, 0.70), _hex(ORANGE_PILL)
    HOVER_TOP, HOVER_BOTTOM = _hex(ORANGE), _hex(ORANGE_DEEP)
    LABEL_COLOR, CORE_COLOR = _hex(TEXT), _hex(TEXT_SOFT)
    HANDLE = _hex(ORANGE)
    ENTER_MS, HOVER_MS, MODE_FADE_MS = (
        MOTION[k] if animations else 1
        for k in ("ENTER_MS", "HOVER_MS", "MODE_FADE_MS"))
    CSS = _CSS % {
        "top": WINDOW_TOP, "bottom": WINDOW_BOTTOM, "alpha": WINDOW_ALPHA,
        "radius": WINDOW_RADIUS, "text": TEXT, "soft": TEXT_SOFT,
        "orange": ORANGE, "sw": SWATCH_PX, "swr": SWATCH_RADIUS,
    }


apply()
