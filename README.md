# Mexerica 🍊

Conversor de arquivos para o GNOME e o Windows 11, inspirado no Tangerine
(macOS). Você **segura Shift enquanto arrasta um arquivo**: uma roda de
formatos aparece em volta do ponteiro. Ao soltar o arquivo num formato, a
cópia convertida é salva ao lado do original. Tudo roda localmente e nada é
enviado para a internet.

Funciona em qualquer arraste de arquivos: Nautilus (Arquivos), área de
trabalho e diálogos. Foi feito para **GNOME Shell 45–51 em Wayland** e
**Windows 11** (Explorer, área de trabalho e diálogos de arquivo). A roda,
as janelas e as operações são as mesmas nos dois.

## Atalhos

| Gesto (durante o arraste)  | Roda                                                   |
|----------------------------|--------------------------------------------------------|
| **Shift**                  | Converter (formatos de saída para aquele tipo)         |
| **Shift + Alt**            | Ferramentas (editar, recortar, cortar, comprimir…)     |
| **Shift + Ctrl**           | Ações (copiar caminho, terminal, copiar/mover, flutuar, ZIP) |
| Soltar no miolo ou fora    | Cancela                                                |
| Soltar o Shift             | A roda some e o arraste segue normal                   |
| **Esc**                    | Cancela o arraste inteiro (comportamento do sistema)   |

Pode trocar de roda sem soltar o arquivo: com Shift já pressionado, aperte
ou solte Alt/Ctrl. A roda continua no mesmo lugar.

## O que faz

**Converter (Shift)**
- **Imagens:** JPG, PNG, WebP, HEIC, AVIF, TIFF, BMP, GIF, ICO e PDF. HEIC e AVIF
  só aparecem se o ImageMagick tiver suporte. SVG vira PNG/JPG/PDF.
- **Vídeo:** MP4, MOV, MKV (sem reencodar), WebM, AVI e GIF animado. Também
  extrai o áudio para MP3, M4A ou WAV.
- **Áudio:** MP3, M4A, WAV, FLAC, OGG, Opus e AIFF.
- **PDF:** PNG ou JPG (uma imagem por página), TXT, DOCX (experimental) e
  XOPP (abre o PDF no Xournal++ para anotar).
- **Xournal++ (.xopp):** PDF. Desenha traços, textos, imagens e fundos
  pautados ou quadriculados; páginas com PDF de fundo mantêm o PDF original
  por baixo, ainda vetorial. Não precisa do Xournal++ instalado; se ele
  estiver, é usado.
- **Documentos do Office:** PDF, DOCX, ODT, RTF, TXT e EPUB; PPTX/ODP; XLSX/ODS/CSV.
- **Texto:** Markdown, HTML e TXT para PDF, DOCX, ODT, HTML, EPUB, MD e TXT.
- **EPUB:** PDF, DOCX, TXT, HTML e MD.
- **Legendas:** SRT, VTT e ASS.
- **Compactados:** extrair (ZIP, 7Z, RAR, TAR.*) ou trocar o formato
  (ZIP, 7Z, TAR.GZ). Uma pasta solta vira ZIP, 7Z ou TAR.GZ.

**Ferramentas (Shift + Alt)**

Na roda, os rótulos das ferramentas e ações ficam em inglês e caixa-alta
(EDIT, CROP, ADD BG…), com um ícone de linha. O miolo mostra o tamanho do
arquivo e, com o ponteiro sobre um setor, o nome dele.

As opções que abrem janela ficam no topo da roda. A janela abre na
hora, e a prévia, as miniaturas e a forma de onda carregam em segundo plano.
**Esc** cancela; **Enter** ou **Ctrl+S** salva. Salvar fecha a janela, e o
trabalho segue com notificação, como as outras operações.

- **Imagem**
  - *EDIT*: recorte com proporção, girar e espelhar (teclas R, L, H, V),
    brilho, contraste, saturação, P&B, escala, formato e qualidade, com
    prévia ao vivo.
  - *CROP* (Crop Image): proporção Free, 1:1, 16:9, 9:16, 4:3 ou 3:4 e
    campos W × H em pixels, sincronizados com o retângulo.
  - *ADD BG* (estilo CleanShot): a imagem com cantos arredondados e sombra
    sobre um gradiente, uma cor (ou cor personalizada) ou outra imagem, com
    margem e proporção. A prévia ao vivo é o mesmo desenho do arquivo
    final. Sempre PNG.
  - *REMOVE BG*: fundo transparente (PNG), em um clique. Sem nada a mais,
    remove fundos lisos (logos, produtos, prints, documentos) a partir dos
    cantos. Com o [rembg](https://github.com/danielgatis/rembg) instalado,
    usa IA e funciona com fotos.
  - *RESIZE*: lado maior ou %, formato, qualidade e peso máximo. Mostra o
    tamanho final real antes de salvar e funciona em lote.
  - Um clique: comprimir, girar 90° e ler QR code (o conteúdo vai para o
    clipboard). Com várias imagens: juntar em PDF e colagem.
- **Vídeo**
  - *Cortar…*: quadros de início e fim, tira de quadros na linha do tempo e
    alças para arrastar. Também dá para remover o trecho e manter o resto.
    O corte rápido (sem recodificar) é instantâneo. Se o quadro-chave
    estiver longe do ponto escolhido, a janela avisa e passa para corte
    exato.
  - *Tamanho…*: caber em 8/10/25/50/100 MB ou outro valor, com resolução
    máxima e sem áudio. Funciona em lote.
  - Um clique: comprimir, sem áudio, 2× velocidade, girar 90° e snapshot do
    quadro do meio. Com vários vídeos: juntar.
- **Áudio:** *Cortar…* (forma de onda e botão para ouvir o trecho, que usa
  o ffplay), normalizar (EBU R128, −16 LUFS), comprimir, mono e tirar
  silêncio. Com vários: juntar.
- **PDF:** *Páginas…* (miniaturas; extrair, apagar ou girar as
  selecionadas), comprimir (Ghostscript), dividir por página, girar 90° e
  extrair imagens. Com vários: juntar.
- **Qualquer mídia:** ver metadados ou remover metadados (EXIF, GPS, autor).

Os presets antigos (`img-1mb`, `img-half`, `img-flip`, `img-gray`,
`vid-25mb`, `vid-10mb`) saíram da roda porque agora estão nas janelas.
Continuam disponíveis em `mexerica run`. `mexerica run img-crop foto.jpg`
abre a janela pelo serviço que já está rodando.

**Ações (Shift + Ctrl):** copiar caminho, abrir terminal na pasta, copiar
para…, mover para…, **flutuar** (uma janelinha sempre visível de onde você
arrasta o arquivo depois) e ZIP de tudo.

**Regras que valem para todas as operações**
- O resultado ganha um sufixo em inglês, que se encadeia:
  `foto Cropped.jpg`, `foto Cropped With Background.png`. Conversão pura só
  troca a extensão.
- Nunca sobrescreve um arquivo: se o nome já existe, vira `foto (2).jpg`.
- Grava primeiro num temporário oculto e só move para o nome final quando
  termina. Se falhar, nenhum arquivo quebrado fica para trás.
- Se a pasta de origem for somente leitura, salva em `~/Downloads`.
- Com vários arquivos, processa todos em lote.
- Mostra uma notificação no início e no fim, com os botões *Mostrar na
  pasta* e *Abrir*. No Windows ela aparece no canto da tela, no mesmo
  vidro das janelas.
- Uma opção só aparece na roda se o programa que ela usa estiver instalado.

## Instalação (Arch Linux)

```bash
# obrigatório
sudo pacman -S --needed python-gobject gtk4
# conversores (instale os que quiser; a roda se adapta)
sudo pacman -S --needed ffmpeg imagemagick libheif librsvg poppler qpdf \
    ghostscript perl-image-exiftool zbar pandoc-cli libreoffice-fresh

git clone https://github.com/rogersocruz/mexerica
cd mexerica
./install.sh          # instala em ~/.local, sem sudo
```

Depois disso, **saia e entre de novo na sessão**. No Wayland o GNOME Shell
só carrega uma extensão nova no login.

Para instalar como pacote do sistema, use o PKGBUILD:
`cd packaging/arch && makepkg -si`.

Para conferir o que foi detectado: `mexerica doctor`. Para desinstalar:
`./uninstall.sh`.

## Instalação (Windows 11)

A interface usa o mesmo GTK 4 do Linux, que no Windows vem do
[MSYS2](https://www.msys2.org). O `install.ps1` instala o MSYS2 pelo
winget se ele não estiver em `C:\msys64`, sem precisar de administrador:

```powershell
git clone https://github.com/rogersocruz/mexerica
cd mexerica
# GTK 4 + PyGObject; com -Converters, também ffmpeg, ImageMagick, poppler,
# qpdf, Ghostscript, librsvg, zbar e libarchive (MSYS2) e Pandoc, ExifTool
# e LibreOffice (winget). A roda se adapta ao que estiver instalado.
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Converters
```

O serviço já sobe no fim da instalação e no login (atalho na pasta
Inicializar). Não precisa sair da sessão. O pacote fica em
`%LOCALAPPDATA%\Mexerica` e o comando `mexerica` entra no PATH do usuário
(vale nos terminais abertos depois). Para conferir: `mexerica doctor`. Para
desinstalar: `.\uninstall.ps1` (o MSYS2 continua instalado).

O MSYS2 em outra pasta: defina `MSYS2_ROOT` antes de rodar o instalador.

## Como funciona

```
 Nautilus ──arraste──► Mutter (compositor)
                          │  sinais dnd-enter / dnd-leave
                          ▼
              Extensão do GNOME Shell ── lê Shift/Alt/Ctrl (30 ms)
                          │             lê os URIs do arraste (seleção DND)
                          │ D-Bus: show(modo, uris, x, y) / hide
                          ▼
         Serviço GTK 4 (mexerica) ── janela transparente em tela cheia,
                          │           colocada acima de tudo pela extensão
                          │           e desenhando a roda (cairo + Pango)
                          │ o arraste passa a "estar sobre" a janela:
                          │ GtkDropTarget recebe hover e drop
                          ▼
                 Motor (Python puro) ── ffmpeg, ImageMagick, LibreOffice,
                                         pandoc, qpdf, Ghostscript, exiftool…
```

**Por que precisa de uma extensão:** no Wayland, durante um arraste o
compositor segura o ponteiro e nenhum aplicativo enxerga o teclado. Uma
extensão do Nautilus também não vê eventos de arraste. O GNOME Shell é o
único processo que roda dentro do compositor e sabe que um arraste começou
e quais teclas estão pressionadas. As APIs (Application Programming
Interfaces) usadas foram conferidas no código-fonte do Mutter e do
gnome-shell: `MetaDnd` emite `dnd-enter` e `dnd-leave` em sessões Wayland, e
a seleção `SELECTION_DND` contém os URIs (Uniform Resource Identifiers)
arrastados.

### No Windows

```
 Explorer ──arraste (OLE)──► imagem de arraste do shell (SysDragImage)
                                  │
         Serviço GTK 4 (mexerica) ── a cada 30 ms: botão do mouse,
                                  │   imagem de arraste e Shift/Alt/Ctrl
                                  │   (GetAsyncKeyState, mesma regra da
                                  │   extensão: mexerica/desktop/drag.py)
                                  ▼
                janela da roda sobre o monitor do ponteiro, acima de
                tudo, com o fundo borrado pelo DWM
                                  │ o arraste do OLE passa a "estar
                                  │ sobre" ela: GtkDropTarget recebe
                                  ▼ hover, os arquivos e o drop
                     Motor (o mesmo) ── ffmpeg, ImageMagick, LibreOffice…
```

No Windows não existe extensão: qualquer processo pode ler o teclado e o
mouse a qualquer momento, e todo arraste do shell mostra uma janela com a
miniatura dos arquivos. O próprio serviço faz o papel da extensão
(`mexerica/desktop/windows.py`): percebe o arraste, coloca a janela da roda
acima de tudo, traz as janelas do serviço para a frente e aplica o vidro.
Os arquivos chegam pelo próprio drop do GTK quando o arraste passa sobre a
roda; se o arraste não tiver arquivos (texto, link), a roda some.

O que muda entre os desktops fica em `mexerica/desktop/`; roda, janelas e
motor são os mesmos.

### Motor sem interface

O motor (`mexerica/engine`) não depende de GTK. Ele também roda pela linha
de comando:

```bash
mexerica list foto.heic              # o que a roda ofereceria
mexerica run to-jpg *.heic           # converte sem interface
mexerica run vid-25mb video.mov
```

Isso permite reaproveitar o motor em Nautilus Scripts ou num menu de
serviço do Dolphin, caso você troque o GNOME pelo KDE (K Desktop
Environment).

## Limitações conhecidas

- **Shift + arrastar no Nautilus normalmente força "mover".** Com a
  Mexerica ativa, o Shift abre a roda. Para mover entre discos, arraste sem
  Shift e escolha *Mover* no menu, ou use Ctrl+X / Ctrl+V.
- **Shift+Alt não abre a roda se Alt+Shift troca o layout do teclado**
  (opção xkb `grp:alt_shift_toggle`). Com essa opção, o Alt vira
  `ISO_Next_Group` e o modificador nunca chega. Remova a opção e troque o
  layout com Super+Espaço:
  `gsettings set org.gnome.desktop.input-sources xkb-options "[]"`.
- **Setas e Enter não funcionam durante o arraste.** O Mutter não entrega
  essas teclas a ninguém enquanto um arraste está em andamento. A escolha é
  feita com o mouse. Fora de um arraste (roda aberta via D-Bus), setas, Enter
  e Esc funcionam.
- **Windows:** Shift durante um arraste no Explorer também força "mover",
  e o Alt pede "criar atalho". Com a roda aberta, o drop vai para ela e o
  original fica onde estava.
- **Windows:** a roda só abre em arrastes do shell (Explorer, área de
  trabalho, diálogos de arquivo e apps que usam a imagem de arraste do
  Windows, como os navegadores). Um app que arraste arquivos sem essa
  imagem não abre a roda.
- **Windows:** o vidro usa uma API não documentada do DWM
  (`SetWindowCompositionAttribute`). Se uma atualização do Windows a
  desligar, as janelas continuam funcionando, só sem o borrão.
- **Windows:** as notificações são da própria Mexerica (no canto da tela),
  não da Central de Notificações: o GLib não tem backend de notificação no
  Windows.
- Ainda não dá para tarjar ou borrar áreas de uma imagem.
- *Cortar…* não toca o vídeo, só mostra quadros. O botão de ouvir toca o
  áudio. O player de vídeo do GTK/GStreamer pode derrubar o processo com
  alguns arquivos, e isso derrubaria a roda junto.
- Não existe equivalente ao AirDrop. Um candidato é o GSConnect/KDE Connect.
- "Juntar vídeos" pressupõe arquivos com a mesma resolução.
- Escala fracionária com layout físico (configuração antiga do Mutter) pode
  deslocar a roda alguns pixels do ponteiro. O padrão atual, layout lógico,
  funciona corretamente.
- Testado até aqui:
  - motor com ffmpeg, ImageMagick, LibreOffice, pandoc, qpdf, Ghostscript e
    exiftool reais (`pytest`);
  - roda e serviço GTK em X virtual, via D-Bus e clique;
  - lógica da extensão com mocks (`node tests/extension_logic.test.mjs`).
  
  **O primeiro teste numa sessão GNOME real é o seu.** Se algo falhar, os
  logs ficam em:
  - `~/.cache/mexerica/mexerica.log` (serviço);
  - `journalctl --user -f -o cat /usr/bin/gnome-shell` (extensão).

  No Windows foram testados o motor e a CLI (com o `tar.exe` do sistema),
  a regra do arraste (`tests/test_drag.py`) e as chamadas Win32 que não
  dependem do GTK (monitor, clipboard, temporário oculto). **A roda e as
  janelas em GTK no Windows ainda não rodaram numa sessão real.** O log fica
  em `%LOCALAPPDATA%\Mexerica\cache\mexerica.log`.

## Desenvolvimento

```bash
make test                       # pytest + teste da extensão (node)
# no Windows (PowerShell, com o Python do MSYS2):
#   C:\msys64\ucrt64\bin\python.exe -m pytest -q tests
# abrir a roda sem arrastar (clique escolhe):
gapplication action io.github.rogersocruz.Mexerica show \
    "('convert', ['file:///caminho/foto.png'], 600, 400)"
```

Para adicionar uma operação, declare um `Op` em `mexerica/engine/ops.py`. Ela
precisa dos tipos de entrada que aceita, dos programas que usa e de um
`build(ctx)` que devolve os comandos. Ela aparece sozinha na roda certa.

### Roadmap
1. Validar numa sessão GNOME real (multi-monitor, escala fracionária).
2. Janela de progresso com cancelamento para jobs longos.
3. Tarjar/borrar áreas no *Editar…*; reordenar páginas no *Páginas…*.
4. Preferências: tecla do gesto, qualidade padrão, pasta de saída.
5. Menu de serviço do Dolphin e Nautilus Scripts reaproveitando o motor.

A lista detalhada está em [TODO.md](TODO.md).

## Licença

MIT. Não tem relação com o Tangerine nem com a Leap Studio. É apenas
inspirado na ideia de interação.
