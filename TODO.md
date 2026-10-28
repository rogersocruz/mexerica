# TODO

## 1. Interface mais clean (vidro claro e quente) — feito

Roda, nomes em inglês, Crop Image e Add BG implementados conforme a
especificação. Cores e medidas estão em `mexerica/theme.py`; as janelas, em
`mexerica/editors/`. Também entrou o REMOVE BG.

Pendências:
- [ ] Comparar com os 4 quadros de referência do Tangerine. Eles não vieram
      com a especificação: salvar em `docs/ref/` e ajustar as diferenças.
- [ ] Abrir as janelas perto do ponteiro. No Wayland, um app não escolhe a
      própria posição; só a extensão poderia movê-las, e a especificação
      pedia para não mexer nela.
- Nota: os ícones são desenhados em `wheel/icons.py` em vez do Adwaita, que não tem
      crop, tag e outros.
- [ ] ANNOTATE e REDACT (citados como exemplo) ainda não existem.

## 2. Modelos 3D (STL, OBJ)

- [ ] Abrir no Blender.
- [ ] Ver numa janela, com uma prévia 3D rápida que gira com o mouse.
- [ ] Edição rápida: escala, girar, centralizar e converter STL ↔ OBJ
      (talvez com o Blender em modo background).

## 3. Executáveis (EXE, AppImage, SH)

- [ ] Detectar os tipos (`.exe`, `.AppImage`, `.sh`, ELF).
- [ ] AppImage e SH: marcar como executável e executar (num terminal, no
      caso do SH).
- [ ] EXE: abrir com o Wine/Bottles, se estiverem instalados.

## 4. Permissões

- [ ] Ação para alterar permissões: tornar executável, só leitura e
      presets 644/755/600.
- [ ] Janela com chmod visual (dono, grupo, outros × leitura, escrita,
      execução).

## 5. Configurações e atalhos

- [ ] Página de configurações.
- [ ] Editar os atalhos (keybindings): a tecla de cada roda (hoje Shift,
      Shift+Alt e Shift+Ctrl).
- [ ] Qualidade padrão e pasta de saída.

## 6. Abrir no VS Code

- [ ] Ação "Abrir no VS Code" para arquivo ou pasta (`code`, `codium` ou o
      Flatpak).

## 7. Xournal++ (XOPP ↔ PDF) — feito

`engine/xopp.py`: XOPP → PDF (cairo + `qpdf --underlay` para PDF de fundo,
ou o próprio `xournalpp`, se instalado) e PDF → XOPP.

- [ ] Fundos raros do Xournal++ (pautas de música, isometrico) saem lisos.
- [ ] Textos usam a API simples do cairo (sem LaTeX/`teximage`).

## 8. Outras plataformas (Windows, KDE, outros Wayland)

O motor (`mexerica/engine`) e a CLI (`mexerica run`) já são independentes
de GNOME. O que muda em cada plataforma é perceber "arraste + modificador"
e mostrar a roda por cima de tudo. Hoje só a extensão do GNOME Shell faz
isso.

- [ ] **Separar a interface por plataforma.** Interface comum: "começou um
      arraste com arquivos", "modificadores mudaram", "mostrar a roda em
      x, y" e "receber o drop". Cada plataforma ganha um backend próprio.
- [ ] **KDE Plasma (Wayland e X11):**
  - Primeiro passo: menus de serviço do Dolphin (`.desktop` em
    `kio/servicemenus`) chamando `mexerica run`, com as ferramentas por
    submenu.
  - Roda durante o arraste: investigar um script ou efeito do KWin que
    observe o DnD e leia os modificadores (o equivalente à extensão do
    GNOME).
  - Visual: o blur do KWin (`org_kde_kwin_blur`) dá o vidro borrado.
- [ ] **Wayland wlroots (Sway, Hyprland) e outros:**
  - Overlay via `wlr-layer-shell` (camada overlay, sem foco).
  - O DnD nesses compositores não expõe os modificadores: talvez seja
    preciso um gatilho alternativo, como um atalho global que abre a roda
    sob o ponteiro e depois um drop nela.
  - Ver se o Hyprland tem um IPC útil (eventos de arraste).
- [ ] **X11 (qualquer desktop):** XDND é visível. Dá para ler os
      modificadores com XInput2/XQueryPointer durante o arraste e mostrar
      uma janela ARGB override-redirect como alvo do drop. Seria o backend
      mais simples depois do GNOME.
- [ ] **Windows 10/11:**
  - O arraste é OLE DoDragDrop. Detectar com um hook de mouse e teclado
    (`SetWindowsHookEx` com `WH_MOUSE_LL` e `WH_KEYBOARD_LL`) e checar o
    formato `CF_HDROP`.
  - Mostrar uma janela topmost em camadas (`WS_EX_LAYERED`) com
    `IDropTarget`. O vidro borrado pode usar Mica ou Acrylic
    (`DwmSetWindowAttribute`).
  - Decidir entre GTK 4 no Windows (MSYS2) e uma interface nativa (WinUI,
    ou Python com pywin32).
  - Dependências: ffmpeg, ImageMagick e qpdf via winget/scoop, e
    `tools.py` resolvendo `.exe`.
  - Empacotamento: instalador (MSIX ou Inno Setup) e um menu de contexto
    do Explorer como alternativa sem roda.
- [ ] **Empacotamento por plataforma:** Flatpak (GNOME e KDE, mas a
      extensão do Shell fica fora do sandbox), AUR (já há PKGBUILD), .deb
      e .rpm.
