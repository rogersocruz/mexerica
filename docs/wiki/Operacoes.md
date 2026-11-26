<!-- Gerada a partir de mexerica/engine/ops.py: não edite à mão. -->
# Operações

Tudo o que as rodas oferecem. Cada item só aparece quando serve para o(s) arquivo(s) arrastado(s) **e** o programa dele está instalado; em [Configurações](Configuracoes.md) dá para tirar itens da roda ou pôr os que vêm fora dela.

A coluna **id** é o nome para a [linha de comando](Linha-de-comando.md): `mexerica run <id> arquivos…`.

## Converter (Shift)

Formatos de saída. A conversão pura só troca a extensão do nome.

### Imagens

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **JPG** | Converte para JPG | — | `to-jpg` | `magick` |
| **PNG** | Converte para PNG | — | `to-png` | `magick` |
| **WEBP** | Converte para WEBP | — | `to-webp` | `magick` |
| **HEIC** | Converte para HEIC | — | `to-heic` | `magick` |
| **AVIF** | Converte para AVIF | — | `to-avif` | `magick` |
| **TIFF** | Converte para TIFF | — | `to-tiff` | `magick` |
| **BMP** | Converte para BMP | — | `to-bmp` | `magick` |
| **GIF** | Converte para GIF | — | `to-gif` | `magick` |
| **ICO** | Converte para ICO | — | `to-ico` | `magick` |
| **PDF** | Converte para PDF | — | `to-pdf` | `magick` |
| **JXL** | Converte para JXL | fora da roda por padrão | `to-jxl` | `magick` |
| **JP2** | Converte para JP2 | fora da roda por padrão | `to-jp2` | `magick` |
| **TGA** | Converte para TGA | fora da roda por padrão | `to-tga` | `magick` |
| **QOI** | Converte para QOI | fora da roda por padrão | `to-qoi` | `magick` |

### Vídeo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **MP4** | Converte para MP4 | — | `to-mp4` | `ffmpeg` |
| **MOV** | Converte para MOV | — | `to-mov` | `ffmpeg` |
| **MKV** | Converte para MKV | — | `to-mkv` | `ffmpeg` |
| **WEBM** | Converte para WEBM | — | `to-webm` | `ffmpeg` |
| **AVI** | Converte para AVI | — | `to-avi` | `ffmpeg` |
| **GIF** | Converte para GIF | — | `to-gif-video` | `ffmpeg` |
| **MP4 HEVC** | Converte para MP4 HEVC — H.265: metade do tamanho do H.264 | sufixo “HEVC”; fora da roda por padrão | `to-mp4-hevc` | `ffmpeg` |
| **MP4 AV1** | Converte para MP4 AV1 — AV1: o menor, e o mais lento de gerar | sufixo “AV1”; fora da roda por padrão | `to-mp4-av1` | `ffmpeg` |

### Áudio

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **MP3** | Converte para MP3 | — | `to-mp3-audio` | `ffmpeg` |
| **M4A** | Converte para M4A | — | `to-m4a-audio` | `ffmpeg` |
| **WAV** | Converte para WAV | — | `to-wav-audio` | `ffmpeg` |
| **FLAC** | Converte para FLAC | — | `to-flac-audio` | `ffmpeg` |
| **OGG** | Converte para OGG | — | `to-ogg-audio` | `ffmpeg` |
| **OPUS** | Converte para OPUS | — | `to-opus-audio` | `ffmpeg` |
| **AIFF** | Converte para AIFF | — | `to-aiff-audio` | `ffmpeg` |

### Legendas

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **SRT** | Converte para SRT | — | `to-srt-sub` | `ffmpeg` |
| **VTT** | Converte para VTT | — | `to-vtt-sub` | `ffmpeg` |
| **ASS** | Converte para ASS | — | `to-ass-sub` | `ffmpeg` |

### Documentos

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PDF** | Converte para PDF | — | `to-pdf-doc` | Office ([quem converte](Documentos-do-Office.md)) |
| **DOCX** | Converte para DOCX | — | `to-docx-doc` | Office ([quem converte](Documentos-do-Office.md)) |
| **ODT** | Converte para ODT | — | `to-odt-doc` | Office ([quem converte](Documentos-do-Office.md)) |
| **RTF** | Converte para RTF | — | `to-rtf-doc` | Office ([quem converte](Documentos-do-Office.md)) |
| **TXT** | Converte para TXT | — | `to-txt-doc` | Office ([quem converte](Documentos-do-Office.md)) |
| **EPUB** | Converte para EPUB — Somente DOCX/ODT | — | `to-epub-doc` | `pandoc` |

### Apresentações

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PDF** | Converte para PDF | — | `to-pdf-slides` | Office ([quem converte](Documentos-do-Office.md)) |
| **PPTX** | Converte para PPTX | — | `to-pptx-slides` | Office ([quem converte](Documentos-do-Office.md)) |
| **ODP** | Converte para ODP | — | `to-odp-slides` | Office ([quem converte](Documentos-do-Office.md)) |

### Planilhas

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PDF** | Converte para PDF | — | `to-pdf-sheet` | Office ([quem converte](Documentos-do-Office.md)) |
| **XLSX** | Converte para XLSX | — | `to-xlsx-sheet` | Office ([quem converte](Documentos-do-Office.md)) |
| **ODS** | Converte para ODS | — | `to-ods-sheet` | Office ([quem converte](Documentos-do-Office.md)) |
| **CSV** | Converte para CSV | — | `to-csv-sheet` | Office ([quem converte](Documentos-do-Office.md)) |

### Texto e Markdown

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PDF** | Converte para PDF | — | `to-pdf-text` | Office ([quem converte](Documentos-do-Office.md)) |
| **DOCX** | Converte para DOCX | — | `to-docx-text` | `pandoc` |
| **ODT** | Converte para ODT | — | `to-odt-text` | `pandoc` |
| **HTML** | Converte para HTML | — | `to-html-text` | `pandoc` |
| **EPUB** | Converte para EPUB | — | `to-epub-text` | `pandoc` |
| **MD** | Converte para MD | — | `to-md-text` | `pandoc` |
| **TXT** | Converte para TXT | — | `to-txt-text` | `pandoc` |

### E-book

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PDF** | Converte para PDF | — | `to-pdf-ebook` | `pandoc` |
| **DOCX** | Converte para DOCX | — | `to-docx-ebook` | `pandoc` |
| **TXT** | Converte para TXT | — | `to-txt-ebook` | `pandoc` |
| **HTML** | Converte para HTML | — | `to-html-ebook` | `pandoc` |
| **MD** | Converte para MD | — | `to-md-ebook` | `pandoc` |
| **EPUB** | Converte para EPUB | — | `to-epub-calibre` | `ebook-convert` |
| **AZW3** | Converte para AZW3 — Kindle | — | `to-azw3-calibre` | `ebook-convert` |
| **MOBI** | Converte para MOBI — Kindle | — | `to-mobi-calibre` | `ebook-convert` |
| **PDF** | Converte para PDF | — | `to-pdf-calibre` | `ebook-convert` |
| **DOCX** | Converte para DOCX | — | `to-docx-calibre` | `ebook-convert` |
| **TXT** | Converte para TXT | — | `to-txt-calibre` | `ebook-convert` |

### PDF

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PNG** | Converte para PNG — Uma imagem por página | gera uma pasta; sufixo “Pages” | `pdf-to-png` | `pdftoppm` |
| **JPG** | Converte para JPG — Uma imagem por página | gera uma pasta; sufixo “Pages” | `pdf-to-jpg` | `pdftoppm` |
| **TXT** | Converte para TXT | — | `pdf-to-txt` | `pdftotext` |
| **DOCX** | Converte para DOCX — Experimental | — | `pdf-to-docx` | Office ([quem converte](Documentos-do-Office.md)) |
| **XOPP** | Converte para XOPP — Abre o PDF para anotar | — | `pdf-to-xopp` | `pdfinfo` |

### Compactados e pastas

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **EXTRAIR** | Extrair | gera uma pasta | `extract` | `bsdtar` |
| **ZIP** | Converte para ZIP | — | `pack-zip` | `bsdtar` |
| **7Z** | Converte para 7Z | — | `pack-7z` | `bsdtar` |
| **TAR.GZ** | Converte para TAR.GZ | — | `pack-tar.gz` | `bsdtar` |

### Xournal++

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PDF** | Converte para PDF — Exporta o caderno | — | `xopp-to-pdf` | `qpdf` |

### Dados

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **JSON** | Converte para JSON | — | `to-json-data` | — |
| **YAML** | Converte para YAML | — | `to-yaml-data` | — |
| **TOML** | Converte para TOML | — | `to-toml-data` | — |
| **XML** | Converte para XML | — | `to-xml-data` | — |
| **CSV** | Converte para CSV — Precisa ser uma lista de registros | — | `to-csv-data` | — |

### Fontes

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **TTF** | Converte para TTF — OTF vira curvas quadráticas | — | `to-ttf-font` | — |
| **OTF** | Converte para OTF — Só de WOFF/WOFF2 com contornos CFF | — | `to-otf-font` | — |
| **WOFF** | Converte para WOFF | — | `to-woff-font` | — |
| **WOFF2** | Converte para WOFF2 — O menor, para sites | — | `to-woff2-font` | — |

## Ferramentas (Shift + Alt)

Processam mantendo o tipo. As que têm … abrem uma janela (veja [Janelas de edição](Janelas-de-edicao.md)).

### Imagens

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **EDITAR** | Editar — Recortar, girar, cor, tamanho | abre janela | `img-edit` | `magick` |
| **RECORTAR** | Recortar — Recorte com proporção | abre janela | `img-crop` | `magick` |
| **FUNDO** | Fundo — Fundo, cantos e sombra | abre janela | `img-addbg` | `magick` |
| **TIRAR FUNDO** | Remover fundo — Fundo transparente (PNG) | sufixo “Without Background” | `img-rmbg` | `magick` |
| **TAMANHO** | Tamanho — Dimensões, qualidade e peso | abre janela | `img-size` | `magick` |
| **COMPRIMIR** | Comprimir — Qualidade 75, sem metadados | sufixo “Compressed” | `img-compress` | `magick` |
| **≤ 1 MB** | ≤ 1 MB — JPG de até 1 MB | sufixo “1MB”; fora da roda por padrão | `img-1mb` | `magick` |
| **50%** | 50% — Reduz pela metade | sufixo “Half”; fora da roda por padrão | `img-half` | `magick` |
| **GIRAR** | Girar 90° | sufixo “Rotated” | `img-rotate` | `magick` |
| **ESPELHAR** | Espelhar | sufixo “Flipped”; fora da roda por padrão | `img-flip` | `magick` |
| **P&B** | P&B | sufixo “Grayscale”; fora da roda por padrão | `img-gray` | `magick` |
| **PARA PDF** | Juntar PDF — Todas as imagens num PDF | vários arquivos → um resultado; sufixo “Merged” | `img-pdf` | `magick` |
| **COLAGEM** | Colagem | vários arquivos → um resultado (mín. 2); sufixo “Collage” | `img-collage` | `montage` |

### Vídeo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **CORTAR** | Cortar — Escolher o trecho | abre janela | `vid-trim` | `ffmpeg`, `ffprobe` |
| **TAMANHO** | Tamanho — Caber em X MB, resolução | abre janela | `vid-size` | `ffmpeg`, `ffprobe` |
| **COMPRIMIR** | Comprimir — H.264 CRF 28 | sufixo “Compressed” | `vid-compress` | `ffmpeg` |
| **≤ 25 MB** | ≤ 25 MB | sufixo “25MB”; fora da roda por padrão | `vid-25mb` | `ffmpeg`, `ffprobe` |
| **≤ 10 MB** | ≤ 10 MB | sufixo “10MB”; fora da roda por padrão | `vid-10mb` | `ffmpeg`, `ffprobe` |
| **SEM SOM** | Sem áudio | sufixo “Muted” | `vid-mute` | `ffmpeg` |
| **2× VELOC.** | 2× vel. | sufixo “2x Speed” | `vid-2x` | `ffmpeg` |
| **GIRAR** | Girar 90° | sufixo “Rotated” | `vid-rotate` | `ffmpeg` |
| **720P** | 720p — No máximo 720 linhas, H.264 | sufixo “720p”; fora da roda por padrão | `vid-720p` | `ffmpeg` |
| **FOTO** | Snapshot — Quadro do meio do vídeo | sufixo “Snapshot” | `vid-snap` | `ffmpeg`, `ffprobe` |
| **JUNTAR** | Juntar — Mesma resolução recomendada | vários arquivos → um resultado (mín. 2); sufixo “Merged” | `vid-join` | `ffmpeg` |

### Áudio

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **CORTAR** | Cortar — Escolher o trecho | abre janela | `aud-trim` | `ffmpeg`, `ffprobe` |
| **NORMALIZAR** | Normalizar — EBU R128, -16 LUFS | sufixo “Normalized” | `aud-normalize` | `ffmpeg` |
| **COMPRIMIR** | Comprimir — MP3 128 kbps | sufixo “Compressed” | `aud-compress` | `ffmpeg` |
| **MONO** | Mono | sufixo “Mono” | `aud-mono` | `ffmpeg` |
| **SILÊNCIO** | Tirar silêncio | sufixo “Without Silence” | `aud-silence` | `ffmpeg` |
| **JUNTAR** | Juntar | vários arquivos → um resultado (mín. 2); sufixo “Merged” | `aud-join` | `ffmpeg` |

### PDF

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PÁGINAS** | Páginas — Reordenar, girar, apagar ou extrair páginas | abre janela | `pdf-pages` | `qpdf`, `pdftoppm` |
| **JUNTAR** | Juntar — Ordenar, girar e apagar páginas antes de juntar | abre janela | `pdf-order` | `qpdf`, `pdftoppm` |
| **DIVIDIR** | Dividir — Página a página, um intervalo ou vários | abre janela | `pdf-cut` | `qpdf`, `pdftoppm` |
| **DESBLOQUEAR** | Desbloquear — Tira a senha e as restrições | abre janela | `pdf-unlock` | `qpdf` |
| **COMPRIMIR** | Comprimir — Ghostscript /ebook | sufixo “Compressed” | `pdf-compress` | `gs` |
| **CADA PÁGINA** | Dividir — Um PDF por página | gera uma pasta; sufixo “Pages”; fora da roda por padrão | `pdf-split` | `qpdf` |
| **GIRAR** | Girar 90° | sufixo “Rotated” | `pdf-rotate` | `qpdf` |
| **IMAGENS** | Extrair imagens | gera uma pasta; sufixo “Images” | `pdf-images` | `pdfimages` |

### Vários tipos

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **SEM METADADOS** | Sem metadados — Remove EXIF/GPS/autor | sufixo “Without Metadata” | `strip-meta` | `exiftool` |

### Qualquer arquivo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **METADADOS** | Metadados — Ler metadados | mostra/copia texto | `show-meta` | `exiftool` |

## Ações (Shift + Ctrl)

Ações de arquivo, sem conversão.

### Qualquer arquivo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **COPIAR CAMINHO** | Copiar caminho | — | `act-copy-path` | — |
| **TERMINAL** | Terminal — Abre um terminal na pasta | — | `act-terminal` | — |
| **COPIAR PARA** | Copiar para | — | `act-copy-to` | — |
| **MOVER PARA** | Mover para | — | `act-move-to` | — |
| **FLUTUAR** | Flutuar — Janela flutuante para arrastar depois | — | `act-float` | — |
| **GERAR QR** | Gerar QR — QR code de um link, salvo na pasta do arquivo | abre janela | `qr-make` | `qrencode` |
| **ZIP** | ZIP — Tudo num ZIP | vários arquivos → um resultado | `act-zip-all` | `bsdtar` |

### Imagens

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **LER QR** | Ler QR — Copia o conteúdo | mostra/copia texto | `img-qr` | `zbarimg` |
