# Como funciona

Três peças: quem **percebe o arraste com Shift** (muda por sistema), o
**serviço GTK 4** que desenha a roda e recebe o drop (o mesmo nos dois) e o
**motor**, que converte (puro Python, sem interface).

## GNOME (Wayland)

```
 Nautilus ──arraste──► Mutter (compositor)
                          │  sinais dnd-enter / dnd-leave
                          ▼
              Extensão do GNOME Shell ── lê Shift/Alt/Ctrl (30 ms)
                          │             lê os URIs do arraste (seleção DND)
                          │ D-Bus: show(modo, uris, x, y) / hide
                          ▼
         Serviço GTK 4 (mexerica) ── janela transparente, maximizada,
                          │           colocada acima de tudo pela extensão
                          │ o arraste passa a "estar sobre" a janela:
                          │ GtkDropTarget recebe hover e drop
                          ▼
                 Motor (Python puro) ── ffmpeg, ImageMagick, Office, pandoc…
```

No Wayland, durante um arraste o compositor segura o ponteiro e nenhum
aplicativo enxerga o teclado. O GNOME Shell é o único processo que roda
dentro do compositor e sabe que um arraste começou e quais teclas estão
pressionadas; por isso existe a extensão
(`extension/mexerica@rogersocruz.github.io`). Ela também:

- põe as janelas do serviço acima das outras e borra o fundo atrás delas
  (o vidro; a tela atrás da roda escurece o quanto as Configurações mandam);
- escreve no clipboard pelo serviço (no Wayland um app sem foco não pode);
- mostra o [ícone na barra superior](Bandeja-e-barra-superior.md) enquanto o
  serviço está no barramento.

## Windows

```
 Explorer ──arraste (OLE)──► imagem de arraste do shell (SysDragImage)
                                  │
         Serviço GTK 4 (mexerica) ── a cada 30 ms: botão do mouse,
                                  │   imagem de arraste e Shift/Alt/Ctrl
                                  │   (mesma regra da extensão: drag.py)
                                  ▼
                janela da roda sobre o monitor do ponteiro, acima de
                tudo, escurecendo e borrando o fundo (DWM)
                                  │ o arraste do OLE passa a "estar
                                  │ sobre" ela: GtkDropTarget recebe
                                  ▼ hover, os arquivos e o drop
                     Motor (o mesmo) ── ffmpeg, ImageMagick, Office…
```

No Windows não existe extensão: qualquer processo lê teclado e mouse, e todo
arraste do shell mostra uma janela com a miniatura dos arquivos. O próprio
serviço faz o papel da extensão (`mexerica/desktop/windows.py`):

- a imagem de arraste marca o **começo**; daí em diante o arraste dura
  enquanto o botão estiver pressionado (sobre a roda o Explorer esconde a
  imagem, e sem essa regra a roda piscaria);
- se o arraste não trouxer arquivos (texto, link), a roda desiste;
- traz as janelas do serviço para a frente, deixa Flutuar e editores acima
  das outras e aplica o vidro;
- clipboard, "mostrar na pasta", abrir, terminal, toasts, a
  [bandeja](Bandeja-e-barra-superior.md) e o arraste nativo da
  [Flutuar](Flutuar.md) pela API do Windows (`win32.py`, só ctypes).

Uma instância só: o GApplication encaminha a segunda para a primeira pelo
D-Bus do GLib; sem ele, um mutex impede a segunda e ela pede à primeira, pela
janela da bandeja, que abra as Configurações.

## O que muda por sistema

Tudo o que muda fica em `mexerica/desktop/`, atrás da mesma interface:

| Peça | GNOME (`gnome.py`) | Windows (`windows.py`, `win32.py`) |
|---|---|---|
| Arraste + Shift | extensão do Shell | o serviço, a cada 30 ms |
| Roda acima de tudo | extensão | `SetWindowPos` topmost |
| Vidro | `Shell.BlurEffect` | DWM (`SetWindowCompositionAttribute`) |
| Clipboard | extensão / wl-copy | `SetClipboardData` |
| Mostrar na pasta | `FileManager1` (D-Bus) | `SHOpenFolderAndSelectItems` |
| Notificações | `Gio.Notification` | toast próprio (`toast.py`) |
| Ícone de "rodando" | barra superior (extensão) | área de notificação |
| Ícone na Flutuar | Nautilus (GIO) | Explorer (`IShellItemImageFactory`) |
| Arraste da Flutuar | `Gtk.DragSource` | `SHDoDragDrop` (nativo) |
| Iniciar com o sistema | `~/.config/autostart` | atalho na pasta Inicializar |

## Motor

`mexerica/engine` não depende de GTK:

- `formats.py`: tipo de cada arquivo pela extensão;
- `ops.py`: cada operação declara os tipos que aceita, os programas de que
  precisa e um `build(ctx)` que devolve os passos (comandos ou funções);
- `runner.py`: executa com as regras de sempre (nunca sobrescreve,
  temporário oculto, lote, pasta de saída);
- `tools.py`: acha os programas (no Windows também na pasta do MSYS2 e onde
  os instaladores costumam pôr LibreOffice, Ghostscript, Pandoc, ExifTool);
- `office.py` + `office.ps1`: [documentos do Office](Documentos-do-Office.md);
- `edits.py`, `background.py`, `xopp.py`: o que as janelas de edição e o
  Xournal++ usam.

## Interface

- `app.py`: o serviço (a janela da roda, a execução dos trabalhos, as
  notificações);
- `wheel/`: geometria e desenho da roda (cairo + Pango), testáveis sem GTK;
- `editors/`: as [janelas de edição](Janelas-de-edicao.md);
- `floating.py`: a [Flutuar](Flutuar.md);
- `settings.py` + `settings_window.py`: as [Configurações](Configuracoes.md);
- `theme.py`: cores, medidas, estilos e CSS.
