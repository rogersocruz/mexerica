"""Catálogo inglês da interface (i18n.py): {português: inglês}.

O português é o texto que está no código. Texto novo na interface precisa
de uma linha aqui; `python tests/i18n_strings.py` lista o que falta e o
test_i18n.py falha enquanto faltar. Os rótulos da roda ficam em
theme.LABELS (inglês) e theme.LABELS_PT.
"""

EN: dict[str, str] = {
    'Cancelado: o Windows pediu permissão de administrador.':
        'Canceled: Windows asked for administrator permission.',
    'O Windows não deixou instalar.':
        "Windows didn't allow the install.",
    'O Windows não deixou remover.':
        "Windows didn't allow the removal.",
    'Ctrl + botão direito sobre arquivos selecionados abre a roda de ações no lugar do menu. Tab passa para a próxima roda (conversão, ferramentas, ações) e Shift+Tab volta; Esc fecha. Ligada, substitui o Shift + arrastar, que deixa de abrir a roda. Sem o Ctrl, o botão direito abre o menu de sempre.':
        'Ctrl + right-click on selected files opens the actions wheel instead of the menu. Tab moves to the next wheel (convert, tools, actions) and Shift+Tab goes back; Esc closes it. When on, it replaces Shift + drag, which no longer opens the wheel. Without Ctrl, right-click opens the usual menu.',
    'Ctrl + botão direito':
        'Ctrl + right-click',
    'Próxima roda':
        'Next wheel',
    'Roda anterior':
        'Previous wheel',
    'Fecha a roda':
        'Closes the wheel',
    'Atalhos':
        'Shortcuts',
    'Com arquivos selecionados, Ctrl + botão direito abre a roda de ações no lugar do menu. Para trocar de roda, role o mouse ou segure Shift, Shift+Alt ou Shift+Ctrl. Sem o Ctrl, nada muda.':
        'With files selected, Ctrl + right-click opens the actions wheel instead of the menu. To switch wheels, scroll or hold Shift, Shift+Alt or Shift+Ctrl. Without Ctrl, nothing changes.',
    'Os formatos principais já vêm incluídos. Os que aparecem sem "Instalado" precisam de um programa instalado à parte.':
        'The main formats are already included. The ones without "Installed" need a program installed separately.',
    'Personalizar':
        'Customize',
    'Cor':
        'Color',
    'Cor do QR':
        'QR color',
    'Transparente':
        'Transparent',
    'Correção':
        'Error correction',
    'Pequeno':
        'Small',
    'Médio':
        'Medium',
    'Baixa':
        'Low',
    'Alta':
        'High',
    'Máxima':
        'Highest',
    'Borda em volta do código. Abaixo de 2, alguns leitores falham.':
        'Border around the code. Below 2, some readers fail.',
    'Quanto do código pode estar danificado e ainda ser lido. Mais alta deixa o código mais denso.':
        'How much of the code can be damaged and still be read. Higher makes the code denser.',
    'SVG fica nítido em qualquer tamanho, bom para impressão.':
        'SVG stays sharp at any size, good for printing.',
    'Pouco contraste: alguns leitores podem não ler este QR.':
        'Low contrast: some readers may not read this QR.',
    'Cor inválida: {color}':
        'Invalid color: {color}',
    'Gerar QR code':
        'Make QR code',
    'Gerar':
        'Make',
    'Nome':
        'Name',
    'Link':
        'Link',
    'Colar o link copiado':
        'Paste the copied link',
    'QR code de um link, salvo na pasta do arquivo':
        "QR code for a link, saved in the file's folder",
    'Teclado':
        'Keyboard',
    # formatos extras (engine/packages.py)
    'Baixando…':
        'Downloading…',
    'Baixar':
        'Download',
    'Baixe o suporte só aos tipos de arquivo que você usa. Remover libera espaço e tira esses itens da roda.':
        'Download support only for the file types you use. Removing frees space and takes those items off the wheel.',
    'Cancelar':
        'Cancel',
    'Compactados':
        'Archives',
    'DOCX, XLSX, PPTX e ODT para PDF, com o layout original':
        'DOCX, XLSX, PPTX and ODT to PDF, keeping the original layout',
    'Desenhos vetoriais com mais fidelidade':
        'Vector drawings with better fidelity',
    'Documentos do Office':
        'Office documents',
    'Documentos e Markdown':
        'Documents and Markdown',
    'E-books':
        'E-books',
    'Formatos extras':
        'Extra formats',
    'Fotos de celular e imagens modernas':
        'Phone photos and modern images',
    'HEIC e AVIF':
        'HEIC and AVIF',
    'Instalado':
        'Installed',
    'Instalado, mas a Mexerica ainda não encontrou o programa. Reinicie a Mexerica.':
        "Installed, but Mexerica hasn't found the program yet. Restart Mexerica.",
    'Instale os programas pelo gerenciador de pacotes do sistema.':
        "Install the programs with the system's package manager.",
    'JPG, PNG, WEBP, GIF, TIFF, BMP e ICO':
        'JPG, PNG, WEBP, GIF, TIFF, BMP and ICO',
    'Juntar, dividir, comprimir e converter PDFs':
        'Merge, split, compress and convert PDFs',
    'Ler e gerar QR codes':
        'Read and make QR codes',
    'MOBI, AZW3 e FB2':
        'MOBI, AZW3 and FB2',
    'MP4, MKV, MOV, WEBM, MP3, WAV, FLAC e OGG':
        'MP4, MKV, MOV, WEBM, MP3, WAV, FLAC and OGG',
    'Markdown, EPUB, DOCX e texto para PDF':
        'Markdown, EPUB, DOCX and text to PDF',
    'Nesta versão, os formatos já vêm incluídos.':
        'In this version, the formats are already included.',
    'Não removido: outros programas usam este pacote ({names}).':
        'Not removed: other programs use this package ({names}).',
    'Não removido: outros programas usam este pacote.':
        'Not removed: other programs use this package.',
    'O gerenciador de pacotes falhou.':
        'The package manager failed.',
    'Os itens da roda que usam esses formatos deixam de aparecer. Dá para baixar de novo depois.':
        'The wheel items that use these formats stop showing up. You can download them again later.',
    'Remova pelo gerenciador de pacotes do sistema.':
        "Remove it with the system's package manager.",
    'Removendo…':
        'Removing…',
    'Remover':
        'Remove',
    'Remover {name}?':
        'Remove {name}?',
    'TTF, OTF, WOFF e WOFF2':
        'TTF, OTF, WOFF and WOFF2',
    'Ver e apagar dados ocultos, como GPS e autor':
        'See and erase hidden data, like GPS and author',
    'Vídeo e áudio':
        'Video and audio',
    'YAML para JSON, CSV e TOML':
        'YAML to JSON, CSV and TOML',
    'ZIP, 7Z, TAR e RAR':
        'ZIP, 7Z, TAR and RAR',
    # só no Linux (tools.PROGRAMS)
    'clipboard sem a extensão (wl-clipboard)':
        'clipboard without the extension (wl-clipboard)',
    'Textos':
        'Text documents',
    '"Ações da Mexerica" no menu do botão direito':
        '"Mexerica actions" in the right-click menu',
    '"{chunk}" não é um intervalo (tente 1-3, 5, 8-)':
        '"{chunk}" is not a range (try 1-3, 5, 8-)',
    '"{chunk}": começa depois de onde termina':
        '"{chunk}": starts after it ends',
    '"{chunk}": o PDF tem as páginas 1 a {total}':
        '"{chunk}": the PDF has pages 1 to {total}',
    '%d/%m/%Y':
        '%m/%d/%Y',
    '(ausente)':
        '(missing)',
    '(inteira)':
        '(full)',
    '1 arquivo':
        '1 file',
    '1 girada':
        '1 rotated',
    '1 página':
        '1 page',
    '1 página fica de fora':
        '1 page left out',
    '1 selecionada':
        '1 selected',
    '2× vel.':
        '2× speed',
    'A cada N páginas':
        'Every N pages',
    'A cópia sai sem senha e sem restrições. O original continua como está.':
        'The copy has no password and no restrictions. The original stays as it is.',
    'A prévia falhou: {err}':
        'Preview failed: {err}',
    'A roda não vai abrir: a detecção de arraste está desligada.':
        "The wheel won't open: drag detection is off.",
    'Abre o DESBLOQUEAR para esses arquivos':
        'Open UNLOCK for these files',
    'Abre o PDF para anotar':
        'Opens the PDF for annotating',
    'Abre um terminal na pasta':
        'Opens a terminal in the folder',
    'Abrir':
        'Open',
    'Abrir a Mexerica':
        'Open Mexerica',
    'Abrir ao entrar no sistema':
        'Open at login',
    'Abrir Configurações':
        'Open Settings',
    'Abrir configurações':
        'Open settings',
    'Abrir o log':
        'Open the log',
    'Adicionar fundo':
        'Add Background',
    'agora':
        'now',
    'Ainda lendo o PDF.':
        'Still reading the PDF.',
    'Ainda lendo os PDFs.':
        'Still reading the PDFs.',
    'Ajustes':
        'Adjust',
    'Alt+Shift e Ctrl+Shift trocam o teclado':
        'Alt+Shift and Ctrl+Shift switch the keyboard',
    'Animações':
        'Animations',
    'Apagar as selecionadas (Delete)':
        'Delete the selected pages (Delete)',
    'Apagar esta página':
        'Delete this page',
    'Aparência':
        'Appearance',
    'Aplicar':
        'Apply',
    'Apresentações':
        'Presentations',
    'Arraste as alças ou digite os tempos.':
        'Drag the handles or type the times.',
    'Arraste para levar o arquivo':
        'Drag to take the file along',
    'Arraste para levar os arquivos':
        'Drag to take the files along',
    'Arraste para mover':
        'Drag to move',
    'Arraste para mover a janela':
        'Drag to move the window',
    'Arraste para reordenar · clique, Ctrl+clique ou Shift+clique para selecionar':
        'Drag to reorder · click, Ctrl+click or Shift+click to select',
    'Arraste sobre a imagem para escolher a área.':
        'Drag on the image to choose an area.',
    'As conversões aparecem aqui, com Abrir e Mostrar na pasta.':
        'Conversions show up here, with Open and Show in folder.',
    'As miniaturas falharam: {err}':
        'Thumbnails failed: {err}',
    'Atalhos durante o arraste':
        'Shortcuts while dragging',
    'até':
        'to',
    'Até 1080 px':
        'Max 1080 px',
    'Até 1280 px':
        'Max 1280 px',
    'Até 1920 px':
        'Max 1920 px',
    'Até 2560 px':
        'Max 2560 px',
    'Até 3840 px':
        'Max 3840 px',
    'Até 512 px':
        'Max 512 px',
    'Até 800 px':
        'Max 800 px',
    'ausente':
        'missing',
    'Automático':
        'Automatic',
    'Automático: português se o sistema estiver em português; inglês nos demais idiomas.':
        'Automatic: Portuguese if the system is in Portuguese; English for any other language.',
    'AV1: o menor, e o mais lento de gerar':
        'AV1: the smallest, and the slowest to make',
    'Avisar quando uma conversão começa':
        'Notify when a conversion starts',
    'Avisos e inicialização':
        'Notifications and startup',
    'Ações':
        'Actions',
    'Ações da Mexerica':
        'Mexerica actions',
    'ações de interface só funcionam pela roda':
        'interface actions only work from the wheel',
    'Baixo para esta resolução: escolha 720p ou 480p.':
        'Low for this resolution: pick 720p or 480p.',
    'Botão direito':
        'Right-click',
    'Brilho':
        'Brightness',
    'Caber em':
        'Fit into',
    'Caber em X MB, resolução':
        'Fit into X MB, resolution',
    'Calculando…':
        'Calculating…',
    'Caminho copiado':
        'Path copied',
    'Cancela':
        'Cancels',
    'Cantos':
        'Corners',
    'Carregando o fundo…':
        'Loading background…',
    'Carregando…':
        'Loading…',
    'clique numa página para começar um arquivo novo nela':
        'click a page to start a new file there',
    'Clique: a primeira página, depois a última':
        'Click: first page, then the last',
    'Colagem':
        'Collage',
    'colagem':
        'collage',
    'Colar (Ctrl+V)':
        'Paste (Ctrl+V)',
    'Cole um link ou escreva um texto':
        'Paste a link or type text',
    'Cole um link ou um texto.':
        'Paste a link or some text.',
    'com senha: {names}':
        'locked (password): {names}',
    'Começar um arquivo novo nesta página':
        'Start a new file at this page',
    'Começo':
        'Start',
    'Começo (s)':
        'Start (s)',
    'Compactados e pastas':
        'Archives and folders',
    'Comportamento':
        'Behavior',
    'Compressão do PNG':
        'PNG compression',
    'Comprimir':
        'Compress',
    'comprimir PDF (Ghostscript)':
        'compress PDF (Ghostscript)',
    'Conferindo…':
        'Checking…',
    'Configurações…':
        'Settings…',
    'Contraste':
        'Contrast',
    'Converta e edite arquivos segurando Shift enquanto arrasta. Tudo acontece no seu computador.':
        'Convert and edit files by holding Shift while you drag. Everything happens on your computer.',
    'Convertendo':
        'Converting',
    'Converter':
        'Convert',
    'Copia o conteúdo':
        'Copies the content',
    'Copiado: 1 item':
        'Copied: 1 item',
    'Copiados: {n} itens':
        'Copied: {n} items',
    'Copiar caminho':
        'Copy path',
    'Copiar para…':
        'Copy to…',
    'Copiar tudo':
        'Copy all',
    'Cor do fundo':
        'Background color',
    'Cores':
        'Colors',
    'Cortar vídeo':
        'Trim Video',
    'Cortar áudio':
        'Trim Audio',
    'Cortar…':
        'Trim…',
    'Corte exato (recodifica): o quadro-chave mais perto fica {gap:.1f} s antes.':
        'Exact cut (re-encodes): nearest keyframe is {gap:.1f} s earlier.',
    'Dados':
        'Data',
    'Das janelas de edição e dos avisos. Menos opaco deixa ver o que está atrás.':
        'Of the editing windows and notifications. Less opaque lets you see what is behind.',
    'de':
        'from',
    'De um link colado (ou copiado antes de abrir)':
        'From a pasted link (or one copied before opening)',
    'Deixa a roda pronta logo depois do login.':
        'Keeps the wheel ready right after login.',
    'Desativa os atalhos do sistema que trocam o idioma do teclado com essas teclas, para elas abrirem as rodas.':
        'Turns off the system shortcuts that switch the keyboard language with these keys, so they open the wheels.',
    'Desbloquear':
        'Unlock',
    'Desbloquear PDF':
        'Unlock PDF',
    'Desbloquear {n} PDFs':
        'Unlock {n} PDFs',
    'Desbloquear…':
        'Unlock…',
    'Desfazer (Ctrl+Z)':
        'Undo (Ctrl+Z)',
    'Desfoque de fundo':
        'Background blur',
    'Desfoque do fundo atrás da roda.':
        'Blur of the background behind the wheel.',
    'Desligado':
        'Off',
    'Digite a senha para abrir o PDF.':
        'Type the password to open the PDF.',
    'Digite os intervalos (por exemplo 1-3, 5, 8-).':
        'Type the ranges (e.g. 1-3, 5, 8-).',
    'Dimensões, qualidade e peso':
        'Dimensions, quality and file size',
    'Disponível só na versão instalada.':
        'Only available in the installed version.',
    'Dividir':
        'Split',
    'Dividir PDF':
        'Split PDF',
    'Dividir…':
        'Split…',
    'Do sistema':
        'System',
    'Do sistema: usa o efeito do próprio sistema. Próprio: a Mexerica desfoca uma imagem da tela, que fica só na memória; funciona mesmo com a transparência do sistema desligada.':
        "System: uses the system's own effect. Own: Mexerica blurs a picture of the screen that stays only in memory; works even with system transparency off.",
    'Documentos':
        'Documents',
    'documentos (LibreOffice, opcional)':
        'documents (LibreOffice, optional)',
    'duração/tamanho alvo':
        'duration/target size',
    'e mais {n}':
        'and {n} more',
    'e-books MOBI, AZW3 e FB2 (calibre, opcional)':
        'MOBI, AZW3 and FB2 e-books (calibre, optional)',
    'Editar imagem':
        'Edit Image',
    'Editar…':
        'Edit…',
    'erro':
        'error',
    'ERRO {src}: {err}':
        'ERROR {src}: {err}',
    'Escala (%)':
        'Scale (%)',
    'Escolher arquivos':
        'Choose files',
    'Escolher arquivos…':
        'Choose files…',
    'Escolher o trecho':
        'Pick the part to keep',
    'Escolher outros…':
        'Choose others…',
    'Escolher…':
        'Choose…',
    'Escurecer a tela':
        'Dim the screen',
    'Espelhar':
        'Mirror',
    'Espelhar na horizontal (H)':
        'Flip horizontal (H)',
    'Espelhar na vertical (V)':
        'Flip vertical (V)',
    'Este PDF pede senha.':
        'This PDF needs a password.',
    'Estes PDFs não estão bloqueados.':
        "These PDFs aren't locked.",
    'Executando':
        'Running',
    'Exporta o caderno':
        'Exports the notebook',
    'Extrair':
        'Extract',
    'Extrair as selecionadas':
        'Extract selected',
    'Extrair imagens':
        'Extract images',
    'extrair imagens de PDF':
        'extract images from PDF',
    'Falhou':
        'Failed',
    'Falhou: {what}':
        'Failed: {what}',
    'falta {what}':
        'missing {what}',
    'Fecha a roda; o arraste continua normal':
        'Closes the wheel; the drag goes on as usual',
    'Fechar':
        'Close',
    'Fechar (Esc)':
        'Close (Esc)',
    'Ferramentas':
        'Tools',
    'Ficaram de fora: {list}':
        'Left out: {list}',
    'Fim':
        'End',
    'Fim (s)':
        'End (s)',
    'Flutuar':
        'Float',
    'Fontes':
        'Fonts',
    'fontes TTF, OTF e WOFF':
        'TTF, OTF and WOFF fonts',
    'fontes WOFF2':
        'WOFF2 fonts',
    'fora da roda por padrão':
        'off the wheel by default',
    'Formato':
        'Format',
    'Fundo':
        'Background',
    'Fundo transparente (PNG)':
        'Transparent background (PNG)',
    'Fundo, cantos e sombra':
        'Background, corners and shadow',
    'Fundo…':
        'Background…',
    'gerar QR code':
        'make QR codes',
    'Gerar QR code…':
        'Make a QR code…',
    'Gerar QR…':
        'Make QR…',
    'Girar 90°':
        'Rotate 90°',
    'Girar e espelhar':
        'Rotate & flip',
    'Girar à direita':
        'Rotate right',
    'Girar à direita (R)':
        'Rotate right (R)',
    'Girar à esquerda':
        'Rotate left',
    'Girar à esquerda (L)':
        'Rotate left (L)',
    'Girar à esquerda (Shift+R)':
        'Rotate left (Shift+R)',
    'Grafite':
        'Graphite',
    'Grande':
        'Large',
    'H.265: metade do tamanho do H.264':
        'H.265: half the size of H.264',
    'há {n} h':
        '{n} h ago',
    'há {n} min':
        '{n} min ago',
    'Idioma':
        'Language',
    'Idioma, cores e efeitos da roda e das janelas.':
        'Language, colors and effects of the wheel and windows.',
    'ilegíveis: {names}':
        "can't read: {names}",
    'ilegível':
        "can't read",
    'Imagem de fundo':
        'Background image',
    'Imagem idêntica à original, arquivo maior. Ignora a qualidade do WEBP.':
        'Image identical to the original, bigger file. Ignores the WEBP quality.',
    'ImageMagick escreve: {list}':
        'ImageMagick writes: {list}',
    'Imagem…':
        'Image…',
    'Imagens':
        'Images',
    'imagens (ImageMagick)':
        'images (ImageMagick)',
    'Indisponível nesta versão.':
        'Not available in this version.',
    'Indisponível: a transparência está desligada nas configurações do sistema.':
        'Unavailable: transparency is off in the system settings.',
    'Intensidade do desfoque':
        'Blur strength',
    'Intervalos':
        'Ranges',
    'Inverter a ordem (das selecionadas, ou de todas)':
        'Reverse the order (of the selected pages, or all)',
    'Início':
        'Home',
    'Isso apagaria todas as páginas.':
        'That would delete every page.',
    'Isso tiraria o arquivo inteiro.':
        'That would remove the whole file.',
    'Item no menu de arquivos e pastas que abre a roda de ações.':
        'An item in the file and folder menu that opens the actions wheel.',
    'Itens da roda':
        'Wheel items',
    'Janela flutuante para arrastar depois':
        'Floating window to drag from later',
    'JPG de até 1 MB':
        'JPG up to 1 MB',
    'Juntar':
        'Merge',
    'Juntar PDF':
        'Merge into PDF',
    'Juntar {n} PDFs':
        'Merge {n} PDFs',
    'juntar/dividir PDF':
        'merge/split PDF',
    'Legendas':
        'Subtitles',
    'Lendo as páginas…':
        'Reading pages…',
    'Lendo…':
        'Reading…',
    'Ler metadados':
        'Read metadata',
    'Ler QR':
        'Read QR',
    'ler QR code (zbar)':
        'read QR codes (zbar)',
    'Liberar Shift+Alt e Shift+Ctrl':
        'Free up Shift+Alt and Shift+Ctrl',
    'Ligue ou desligue os itens de cada roda. Cada item só aparece para os arquivos em que funciona. Itens apagados precisam de um programa que não está instalado. Passe o mouse para ver o que cada um faz.':
        "Turn each wheel's items on or off. Each item only shows up for the files it works on. Dimmed items need a program that isn't installed. Hover to see what each one does.",
    'Limpar':
        'Clear',
    'Livre':
        'Free',
    'Margem':
        'Padding',
    'Markdown/EPUB e documentos sem Office':
        'Markdown/EPUB and documents without Office',
    'Menta':
        'Mint',
    'Mesma resolução recomendada':
        'Same resolution recommended',
    'Metadados':
        'Metadata',
    'metadados':
        'metadata',
    'Mexerica':
        'Mexerica',
    'Mexerica: arraste um arquivo e segure Shift':
        'Mexerica: drag a file and hold Shift',
    'Mostrar':
        'Show',
    'Mostrar na pasta':
        'Show in folder',
    'Mover para…':
        'Move to…',
    'Movido: 1 item':
        'Moved: 1 item',
    'Movidos: {n} itens':
        'Moved: {n} items',
    'Movimento ao abrir a roda e ao passar o mouse pelos itens.':
        'Motion when the wheel opens and when hovering over items.',
    'Média':
        'Medium',
    'módulo Python':
        'Python module',
    'Na hora e sem perda. No vídeo, o começo pode voltar até o quadro-chave anterior; desligue para um corte exato.':
        'Instant and lossless. For video the start may move back to the previous keyframe; turn off for an exact cut.',
    'Na mesma pasta do arquivo original':
        'In the same folder as the original file',
    'Nada a fazer com esses arquivos. Se faltar um programa, Sobre mostra quais foram encontrados.':
        'Nothing to do with these files. If a program is missing, About shows which ones were found.',
    'Nada mudou ainda.':
        'Nothing changed yet.',
    'Nada mudou ainda: arraste, gire ou apague páginas antes.':
        'Nothing changed yet: drag, rotate or delete pages first.',
    'Nada mudou: escolha um tamanho, formato ou limite.':
        'Nothing changed: pick a size, format or limit.',
    'Nada para desbloquear: estes PDFs não estão bloqueados.':
        "Nothing to unlock: these PDFs aren't locked.",
    'Nada selecionado':
        'Nothing selected',
    'nenhum arquivo':
        'no files',
    'Nenhum arquivo é substituído: se o nome já existir, o novo vira "foto (2).jpg".':
        'No file is ever replaced: if the name exists, the new one becomes "photo (2).jpg".',
    'nenhum extra':
        'no extras',
    'Nenhum link neste arquivo: cole um':
        'No links in this file: paste one',
    'Nenhum QR code encontrado':
        'No QR code found',
    'Nenhuma':
        'None',
    'Nenhuma página escolhida.':
        'No page chosen.',
    'Nenhuma página para mostrar.':
        'No pages to show.',
    'ninguém':
        'nobody',
    'No máximo 720 linhas, H.264':
        'At most 720 lines, H.264',
    'Normalizar':
        'Normalize',
    'Não deu para abrir a imagem: {err}':
        'Could not open the image: {err}',
    'Não deu para abrir o fundo: {err}':
        'Could not open the background: {err}',
    'Não deu para gerar este QR: {err}':
        "Can't make this QR: {err}",
    'Não deu para ler a duração: {err}':
        'Could not read the duration: {err}',
    'Não deu para ler o arquivo: {err}':
        'Could not read the file: {err}',
    'Não deu para ler o PDF: {err}':
        'Could not read the PDF: {err}',
    'Não deu para ler os PDFs: {err}':
        'Could not read the PDFs: {err}',
    'não está mais lá':
        'no longer there',
    'Não muda a imagem. Mais alta: arquivo menor, conversão mais lenta.':
        "Doesn't change the image. Higher: smaller file, slower conversion.",
    'Não sobrou nenhuma página.':
        'No pages left.',
    'O aviso de conclusão aparece sempre.':
        'The done notification always shows up.',
    'O corte rápido começa em {t} (quadro-chave), {gap:.1f} s antes. Desligue o “Rápido” para um corte exato.':
        'Fast cut starts at {t} (keyframe), {gap:.1f} s early. Turn off “Fast” for an exact cut.',
    'O corte rápido começa exatamente onde você escolheu.':
        'Fast cut starts exactly where you chose.',
    'O intervalo começa em {a}, depois de onde termina ({b}).':
        'The range starts at {a}, after it ends ({b}).',
    'O mais curto: {t}.':
        'Shortest: {t}.',
    'O menor, para sites':
        'The smallest, for websites',
    'O trecho é curto demais.':
        'Selection is too short.',
    'O trecho é o arquivo inteiro: mexa nas alças.':
        'The selection is the whole file: move the handles.',
    'Oceano':
        'Ocean',
    'Onde salvar':
        'Where to save',
    'Onde salvar os arquivos, qualidade e avisos.':
        'Where to save files, quality and notifications.',
    'ontem':
        'yesterday',
    'Opacidade das janelas':
        'Window opacity',
    'operação desconhecida: {op}':
        'unknown operation: {op}',
    'Ordenar, girar e apagar páginas antes de juntar':
        'Order, rotate and delete pages before merging',
    'Original':
        'Original',
    'OTF vira curvas quadráticas':
        'OTF becomes quadratic curves',
    'Outra cor':
        'Custom',
    'Outros':
        'Other',
    'Outro…':
        'Custom…',
    'Ouvir o trecho (Espaço)':
        'Play the selection (Space)',
    'ouvir o trecho no Cortar…':
        'play the selection in Trim…',
    'P&B':
        'B&W',
    'Pague me um café':
        'Buy me a coffee',
    'pandoc + typst (só o conteúdo, sem layout)':
        'pandoc + typst (content only, no layout)',
    'Para essas teclas abrirem as rodas, desative os atalhos do sistema que trocam o idioma do teclado com elas:':
        'For these keys to open the wheels, turn off the system shortcuts that switch the keyboard language with them:',
    'Para instalar o que falta: .\\install.ps1 -Converters (LibreOffice: -Office)':
        "To install what's missing: .\\install.ps1 -Converters (LibreOffice: -Office)",
    'para {folder}':
        'to {folder}',
    'PDF pelo pandoc, sem Office':
        'PDF through pandoc, without Office',
    'PDF → imagens (poppler)':
        'PDF → images (poppler)',
    'PDF → texto':
        'PDF → text',
    'pede senha':
        'needs the password',
    'Pequena':
        'Small',
    'Peso máximo (JPG)':
        'Max file size (JPG)',
    'Planilhas':
        'Spreadsheets',
    'PNG, salvo ao lado do original':
        'PNG, saved next to the original',
    'Precisa ser uma lista de registros':
        'Must be a list of records',
    'Preto e branco':
        'Black & white',
    'Primeira imagem: ':
        'First image: ',
    'Processando':
        'Processing',
    'Pronto: {name}':
        'Done: {name}',
    'Pronto: {n} arquivos':
        'Done: {n} files',
    'Proporção':
        'Aspect ratio',
    'Próprio':
        'Own',
    'Página a página':
        'Single pages',
    'Página a página, um intervalo ou vários':
        'Single pages, one range or several',
    'Páginas do PDF':
        'PDF Pages',
    'páginas por arquivo':
        'pages per file',
    'Páginas…':
        'Pages…',
    'QR code':
        'QR Code',
    'QR code de um link do arquivo ou colado':
        'QR code from a link in the file or pasted',
    'QR copiado':
        'QR copied',
    'Quadro do meio do vídeo':
        'Frame from the middle of the video',
    'Qualidade':
        'Quality',
    'Qualidade 75, sem metadados':
        'Quality 75, no metadata',
    'Qualidade das imagens':
        'Image quality',
    'Qualidade do {fmt}':
        '{fmt} quality',
    'Qualquer arquivo':
        'Any file',
    'Quanto a tela atrás da roda fica mais escura.':
        'How much darker the screen behind the wheel gets.',
    'Recentes':
        'Recent',
    'Recortar imagem':
        'Crop Image',
    'Recortar, girar, cor, tamanho':
        'Crop, rotate, color, size',
    'Recortar…':
        'Crop…',
    'Recorte':
        'Crop',
    'Recorte com proporção':
        'Crop with an aspect ratio',
    'Reduz pela metade':
        'Halves the size',
    'Remove EXIF/GPS/autor':
        'Removes EXIF/GPS/author',
    'Remover fundo':
        'Remove background',
    'remover fundo de fotos com IA (opcional)':
        'remove photo backgrounds with AI (optional)',
    'Reordenar, girar, apagar ou extrair páginas':
        'Reorder, rotate, delete or extract pages',
    'Resolução máxima':
        'Max resolution',
    'Restaurar':
        'Reset',
    'Restaurar o padrão':
        'Restore defaults',
    'Roda com Ctrl + botão direito':
        'Wheel on Ctrl + right-click',
    'Roda de ações':
        'Actions wheel',
    'Roda de conversão':
        'Conversion wheel',
    'Roda de ferramentas':
        'Tools wheel',
    'Roda e janelas':
        'Wheel and windows',
    'Rápido (sem recodificar)':
        'Fast (no re-encode)',
    'Sair da Mexerica':
        'Quit Mexerica',
    'salva ao lado da original':
        'saved next to the original',
    'Salvar':
        'Save',
    'Salvar com fundo':
        'Save with Background',
    'Salvo ao lado de {name}':
        'Saved next to {name}',
    'Salvo em {folder}':
        'Saved in {folder}',
    'Saturação':
        'Saturation',
    'Saída':
        'Output',
    'Selecione as páginas para apagar.':
        'Select the pages to delete.',
    'Selecione as páginas para extrair.':
        'Select the pages to extract.',
    'Selecione as páginas para girar.':
        'Select the pages to rotate.',
    'Selecione os arquivos e use Ctrl + clique direito de novo.':
        'Select the files and Ctrl + right-click again.',
    'sem bloqueio':
        'not locked',
    'Sem limite':
        'No limit',
    'Sem metadados':
        'No metadata',
    'Sem prévia: {err}':
        'No preview: {err}',
    'Sem áudio':
        'Mute',
    'Sempre nesta pasta:':
        'Always in this folder:',
    'Senha':
        'Password',
    'Senha errada.':
        'Wrong password.',
    'serviço não respondeu: {err}':
        "the service didn't answer: {err}",
    'Sobre':
        'About',
    'Soltar no centro da roda':
        'Drop in the center of the wheel',
    'Soltar o Shift':
        'Release Shift',
    'Solte arquivos aqui':
        'Drop files here',
    'Solte ou escolha arquivos para ver tudo o que dá para fazer com eles.':
        'Drop or choose files to see everything you can do with them.',
    'Sombra':
        'Shadow',
    'Somente DOCX/ODT':
        'DOCX/ODT only',
    'São as teclas das rodas de ferramentas e de ações. Desligue esses atalhos nas Configurações do Windows e troque o teclado com Win+Espaço ({steps}).':
        'They are the keys for the tools and actions wheels. Turn those shortcuts off in Windows Settings and switch keyboards with Win+Space ({steps}).',
    'Só de WOFF/WOFF2 com contornos CFF':
        'Only from WOFF/WOFF2 with CFF outlines',
    'Só qualidade (CRF 26)':
        'Quality only (CRF 26)',
    'só restrições':
        'restrictions only',
    'Tamanho':
        'Size',
    'Tamanho (MB)':
        'Size (MB)',
    'Tamanho da roda':
        'Wheel size',
    'Tamanho do vídeo':
        'Resize Video',
    'Tamanho…':
        'Resize…',
    'Teclado avançado > Teclas de atalho do idioma de entrada > Alterar sequência de teclas: "Não atribuído" nas duas':
        'Advanced keyboard settings > Input language hot keys > Change Key Sequence: "Not Assigned" for both',
    'Texto e Markdown':
        'Text and Markdown',
    'Tipo de desfoque':
        'Blur type',
    'Tira a senha e as restrições':
        'Removes the password and restrictions',
    'Tirar o trecho (manter o resto)':
        'Remove selection (keep the rest)',
    'Tirar o áudio':
        'Remove audio',
    'Tirar silêncio':
        'Remove silence',
    'Todas':
        'All',
    'Todas as imagens num PDF':
        'All images in one PDF',
    'Tudo num ZIP':
        'All in one ZIP',
    'um conversor':
        'a converter',
    'Um intervalo':
        'One range',
    'Um PDF novo só com as páginas selecionadas, nesta ordem e rotação':
        'A new PDF with only the selected pages, in this order and rotation',
    'um PDF por página':
        'one PDF per page',
    'Um PDF por página':
        'One PDF per page',
    'Uma imagem por página':
        'One image per page',
    'Usada ao converter para cada formato. Mais alta: imagem melhor e arquivo maior.':
        'Used when converting to each format. Higher: better image and bigger file.',
    'Uva':
        'Grape',
    'Ver log':
        'View log',
    'Vários tipos':
        'Several types',
    'Vídeo':
        'Video',
    'Vídeo a ~{kbps:.0f} kbps.':
        'Video at ~{kbps:.0f} kbps.',
    'vídeo e áudio':
        'video and audio',
    'WEBP sem perda':
        'Lossless WEBP',
    '{group}  ·  na roda: {keys}':
        '{group}  ·  on the wheel: {keys}',
    '{i}  ·  arquivo {k}':
        '{i}  ·  file {k}',
    '{name}, página {page}':
        '{name}, page {page}',
    '{n} arquivo(s), {size}, {time} no total.':
        '{n} file(s), {size}, {time} total.',
    '{n} arquivos':
        '{n} files',
    '{n} falharam':
        '{n} failed',
    '{n} giradas':
        '{n} rotated',
    '{n} imagens':
        '{n} images',
    '{n} itens':
        '{n} items',
    '{n} links em {name}':
        '{n} links in {name}',
    '{n} páginas':
        '{n} pages',
    '{n} páginas ficam de fora':
        '{n} pages left out',
    '{n} selecionadas':
        '{n} selected',
    '{n} vídeos':
        '{n} videos',
    '{pos} (p.{page})':
        '{pos} (p.{page})',
    '{pos} · {name} p.{page}':
        '{pos} · {name} p.{page}',
    'Áudio':
        'Audio',
}

# Iguais nos dois idiomas (formatos, siglas, unidades, marcas).
SAME: set[str] = {
    "Mexerica", "Kindle", "Mono", "Terminal", "Snapshot", "Experimental",
    "Ghostscript /ebook", "EBU R128, -16 LUFS", "H.264 CRF 28",
    "MP3 128 kbps", "MP4 AV1", "MP4 HEVC", "YAML (PyYAML)",
    "ZIP/7Z/TAR/RAR (libarchive)", "TAR.GZ", "px", "W", "H", "SVG", "PNG",
    "small", "medium", "large", "win32", "Original",
    "{pos} (p.{page})", "{pos} · {name} p.{page}",
}
