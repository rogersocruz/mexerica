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

### Vídeo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **MP4** | Converte para MP4 | — | `to-mp4` | `ffmpeg` |
| **MOV** | Converte para MOV | — | `to-mov` | `ffmpeg` |
| **MKV** | Converte para MKV | — | `to-mkv` | `ffmpeg` |
| **WEBM** | Converte para WEBM | — | `to-webm` | `ffmpeg` |
| **AVI** | Converte para AVI | — | `to-avi` | `ffmpeg` |
| **GIF** | Converte para GIF | — | `to-gif-video` | `ffmpeg` |

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
| **EXTRACT** | Extrair | gera uma pasta | `extract` | `bsdtar` |
| **ZIP** | Converte para ZIP | — | `pack-zip` | `bsdtar` |
| **7Z** | Converte para 7Z | — | `pack-7z` | `bsdtar` |
| **TAR.GZ** | Converte para TAR.GZ | — | `pack-tar.gz` | `bsdtar` |

### Xournal++

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PDF** | Converte para PDF — Exporta o caderno | — | `xopp-to-pdf` | `qpdf` |

## Ferramentas (Shift + Alt)

Processam mantendo o tipo. As que têm … abrem uma janela (veja [Janelas de edição](Janelas-de-edicao.md)).

### Imagens

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **EDIT** | Editar — Recortar, girar, cor, tamanho | abre janela | `img-edit` | `magick` |
| **CROP** | Recortar — Recorte com proporção | abre janela | `img-crop` | `magick` |
| **ADD BG** | Fundo — Fundo, cantos e sombra | abre janela | `img-addbg` | `magick` |
| **REMOVE BG** | Remover fundo — Fundo transparente (PNG) | sufixo “Without Background” | `img-rmbg` | `magick` |
| **RESIZE** | Tamanho — Dimensões, qualidade e peso | abre janela | `img-size` | `magick` |
| **COMPRESS** | Comprimir — Qualidade 75, sem metadados | sufixo “Compressed” | `img-compress` | `magick` |
| **≤ 1 MB** | ≤ 1 MB — JPG de até 1 MB | sufixo “1MB”; fora da roda por padrão | `img-1mb` | `magick` |
| **50%** | 50% — Reduz pela metade | sufixo “Half”; fora da roda por padrão | `img-half` | `magick` |
| **ROTATE** | Girar 90° | sufixo “Rotated” | `img-rotate` | `magick` |
| **ESPELHAR** | Espelhar | sufixo “Flipped”; fora da roda por padrão | `img-flip` | `magick` |
| **P&B** | P&B | sufixo “Grayscale”; fora da roda por padrão | `img-gray` | `magick` |
| **READ QR** | Ler QR — Copia o conteúdo | mostra/copia texto | `img-qr` | `zbarimg` |
| **TO PDF** | Juntar PDF — Todas as imagens num PDF | vários arquivos → um resultado; sufixo “Merged” | `img-pdf` | `magick` |
| **COLLAGE** | Colagem | vários arquivos → um resultado (mín. 2); sufixo “Collage” | `img-collage` | `montage` |

### Vídeo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **TRIM** | Cortar — Escolher o trecho | abre janela | `vid-trim` | `ffmpeg`, `ffprobe` |
| **RESIZE** | Tamanho — Caber em X MB, resolução | abre janela | `vid-size` | `ffmpeg`, `ffprobe` |
| **COMPRESS** | Comprimir — H.264 CRF 28 | sufixo “Compressed” | `vid-compress` | `ffmpeg` |
| **≤ 25 MB** | ≤ 25 MB | sufixo “25MB”; fora da roda por padrão | `vid-25mb` | `ffmpeg`, `ffprobe` |
| **≤ 10 MB** | ≤ 10 MB | sufixo “10MB”; fora da roda por padrão | `vid-10mb` | `ffmpeg`, `ffprobe` |
| **MUTE** | Sem áudio | sufixo “Muted” | `vid-mute` | `ffmpeg` |
| **2× SPEED** | 2× vel. | sufixo “2x Speed” | `vid-2x` | `ffmpeg` |
| **ROTATE** | Girar 90° | sufixo “Rotated” | `vid-rotate` | `ffmpeg` |
| **SNAPSHOT** | Snapshot — Quadro do meio do vídeo | sufixo “Snapshot” | `vid-snap` | `ffmpeg`, `ffprobe` |
| **JOIN** | Juntar — Mesma resolução recomendada | vários arquivos → um resultado (mín. 2); sufixo “Merged” | `vid-join` | `ffmpeg` |

### Áudio

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **TRIM** | Cortar — Escolher o trecho | abre janela | `aud-trim` | `ffmpeg`, `ffprobe` |
| **NORMALIZE** | Normalizar — EBU R128, -16 LUFS | sufixo “Normalized” | `aud-normalize` | `ffmpeg` |
| **COMPRESS** | Comprimir — MP3 128 kbps | sufixo “Compressed” | `aud-compress` | `ffmpeg` |
| **MONO** | Mono | sufixo “Mono” | `aud-mono` | `ffmpeg` |
| **SILENCE** | Tirar silêncio | sufixo “Without Silence” | `aud-silence` | `ffmpeg` |
| **JOIN** | Juntar | vários arquivos → um resultado (mín. 2); sufixo “Merged” | `aud-join` | `ffmpeg` |

### PDF

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **PAGES** | Páginas — Extrair, apagar ou girar páginas | abre janela | `pdf-pages` | `qpdf`, `pdftoppm` |
| **COMPRESS** | Comprimir — Ghostscript /ebook | sufixo “Compressed” | `pdf-compress` | `gs` |
| **SPLIT** | Dividir — Um PDF por página | gera uma pasta; sufixo “Pages” | `pdf-split` | `qpdf` |
| **ROTATE** | Girar 90° | sufixo “Rotated” | `pdf-rotate` | `qpdf` |
| **IMAGES** | Extrair imagens | gera uma pasta; sufixo “Images” | `pdf-images` | `pdfimages` |
| **MERGE** | Juntar | vários arquivos → um resultado (mín. 2); sufixo “Merged” | `pdf-merge` | `qpdf` |

### Vários tipos

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **STRIP META** | Sem metadados — Remove EXIF/GPS/autor | sufixo “Without Metadata” | `strip-meta` | `exiftool` |

### Qualquer arquivo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **METADATA** | Metadados — Ler metadados | mostra/copia texto | `show-meta` | `exiftool` |

## Ações (Shift + Ctrl)

Ações de arquivo, sem conversão.

### Qualquer arquivo

| Na roda | O que faz | Detalhes | id | Precisa de |
|---|---|---|---|---|
| **COPY PATH** | Copiar caminho | — | `act-copy-path` | — |
| **TERMINAL** | Terminal — Abre um terminal na pasta | — | `act-terminal` | — |
| **COPY TO** | Copiar para | — | `act-copy-to` | — |
| **MOVE TO** | Mover para | — | `act-move-to` | — |
| **FLOAT** | Flutuar — Janela flutuante para arrastar depois | — | `act-float` | — |
| **ZIP** | ZIP — Tudo num ZIP | vários arquivos → um resultado | `act-zip-all` | `bsdtar` |
