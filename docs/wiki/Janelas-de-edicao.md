# Janelas de edição

Alguns itens da roda de **Ferramentas** abrem uma janela (ficam no topo da
roda). Ela aparece na hora; a prévia, as miniaturas e a forma de onda
carregam em segundo plano. Todas seguem o mesmo jeito:

- cabeçalho com **×** e o título (arraste por ele para mover);
- rodapé com **Reset** à esquerda e a ação principal à direita;
- **Esc** fecha; **Enter** ou **Ctrl+S** executa;
- salvar fecha a janela, e o trabalho segue com notificação, como as outras
  operações (nunca sobrescreve, temporário oculto, etc.).

O visual (vidro na cor do estilo e opacidade) muda em
[Configurações](Configuracoes.md).

## Imagem

### EDIT — Edit Image

Recorte com proporção, girar e espelhar, brilho, contraste, saturação, preto
e branco, escala, formato e qualidade, com prévia ao vivo.
Teclas: **R** gira à direita, **L** à esquerda, **H** espelha na horizontal,
**V** na vertical.

### CROP — Crop Image

Proporção **Free, 1:1, 16:9, 9:16, 4:3 ou 3:4** e campos **W × H** em pixels,
sincronizados com o retângulo. Arraste as alças ou o retângulo.

### ADD BG — Add Background

No estilo CleanShot: a imagem com cantos arredondados e sombra sobre um
gradiente, uma cor (ou cor personalizada) ou outra imagem, com margem e
proporção (Auto, 1:1, 16:9, 4:5). A prévia é o mesmo desenho do arquivo
final. Sai sempre em PNG.

### REMOVE BG (sem janela)

Fundo transparente (PNG) em um clique. Sem nada a mais, remove fundos lisos
(logos, produtos, prints, documentos) a partir dos cantos. Com o
[rembg](https://github.com/danielgatis/rembg) instalado, usa IA e funciona
com fotos.

### RESIZE — Resize (em lote)

Tamanho (Original, 75%, 50%, 25% ou lado maior de 3840 a 512 px), formato,
qualidade e **peso máximo** (100 KB a 5 MB). Mostra o tamanho final real
antes de salvar. Funciona com várias imagens.

## Vídeo e áudio

### TRIM — Trim Video / Trim Audio

- Vídeo: quadros de início e fim, tira de quadros na linha do tempo e alças
  para arrastar.
- Áudio: forma de onda e botão de ouvir o trecho (**Espaço**; usa o
  `ffplay`).
- **Fast (no re-encode):** corte instantâneo e sem perda. Se o quadro-chave
  estiver longe do ponto escolhido, a janela avisa e passa para corte exato.
- **Remove selection:** tira o trecho e junta o resto.

### RESIZE — Resize Video (em lote)

Caber em 8, 10, 25, 50 ou 100 MB (ou outro valor), ou só qualidade (CRF 26);
resolução máxima (1080p a 360p) e opção sem áudio. Mostra o bitrate que vai
sair e avisa quando é baixo para a resolução.

## PDF

### O organizador de páginas (PÁGINAS e JUNTAR)

As duas janelas mostram as páginas numa grade e funcionam igual:

- **Selecionar:** clique; **Ctrl+clique** soma; **Shift+clique** pega um
  trecho; **Ctrl+A** todas.
- **Reordenar:** arraste uma página (ou as selecionadas). Enquanto você
  arrasta, as outras páginas abrem espaço e a arrastada fica tracejada no
  lugar onde vai entrar; **soltar** confirma a ordem, **Esc** (ou soltar
  fora da grade) volta ao que era. Perto da borda, a grade rola sozinha.
  **Alt+←/→** move as selecionadas.
- **Girar:** ↺/↻ no canto da miniatura (aparecem ao passar o mouse), na
  barra de cima, ou **R** / **Shift+R** nas selecionadas. A miniatura gira
  junto e mostra o ângulo.
- **Apagar:** ✕ na miniatura, a lixeira ou **Delete**.
- **Inverter:** inverte a ordem das selecionadas (ou de todas, sem seleção).
- **Ctrl+Z** desfaz; **Reset** volta ao PDF original.

### PAGES — PDF Pages

Um PDF no organizador. **Save** grava uma cópia com a nova ordem, rotações
e sem as páginas apagadas (`relatório Edited.pdf`). **Extract selected**
grava só as páginas selecionadas, na ordem e rotação da tela
(`relatório Pages 2 5.pdf`).

### SPLIT — Split PDF

- **Single pages:** um PDF por página.
- **One range:** um PDF só com o trecho escolhido (de… até…), solto ao lado
  do original (`relatório 3-7.pdf`). Clicar numa página marca o começo;
  o segundo clique, o fim.
- **Ranges:** vários trechos, como `1-3, 4-8, 9-` (`9-` vai até o fim,
  `-4` começa na primeira). Cada trecho vira um arquivo; trechos podem
  pular páginas ou se repetir. **Clique numa página** para começar um
  arquivo novo nela, como uma tesoura; clique de novo para desfazer.
- **Every N pages:** um arquivo a cada N páginas.
- Com mais de uma parte, os PDFs vão numa pasta (`relatório Parts`, com
  `relatório 1-3.pdf`, `relatório 4-8.pdf`…). Cada miniatura mostra a que
  arquivo vai; as que ficam de fora aparecem apagadas.

Um PDF por página sem abrir janela continua existindo (**EVERY PAGE**),
fora da roda por padrão: ligue em Configurações > Itens da roda.

### JUNTAR — juntar PDFs

Selecione de 2 a N PDFs, arraste com **Shift+Alt** e solte em **JUNTAR**
(*MERGE* em inglês).
Abre o organizador com **todas as páginas de todos os arquivos**, na ordem
em que os arquivos aparecem **na lista do Explorer** (a mesma ordem da tela,
com a ordenação que a pasta estiver usando) e, dentro de cada arquivo, na
ordem das páginas. Cada página tem uma faixa da cor do arquivo de origem e
o rótulo `posição · arquivo p.N`. Reordene, inverta, gire e apague páginas;
**Merge** grava um PDF só, com o nome do primeiro arquivo e o sufixo
`Merged`.

- No Windows a ordem vem da janela do Explorer de onde os arquivos saíram.
  Sem ela (arraste de outro programa), os arquivos vão em ordem de nome
  (`R0`, `R0-1`, `R0-2`… `R0-10`). No Linux, na ordem do gerenciador de
  arquivos.
- PDF com senha fica de fora, com um aviso e o botão **Unlock…**.
- Há um Juntar só: o que abre esta tela. O antigo juntar direto, sem
  tela, saiu.

### UNLOCK — desbloquear PDF

Para um ou mais PDFs. Mostra o estado de cada um (*not locked*,
*restrictions only* ou *needs the password*). PDFs só com restrições
(imprimir, copiar, editar) saem livres sem senha; os que pedem senha para
abrir usam a senha digitada. O resultado é uma cópia sem senha e sem
restrições (`contrato Unlocked.pdf`); o original não muda. A senha só vai
para o `qpdf`, pela entrada padrão: não aparece na linha de comando nem no
log.

## Texto e links

### GERAR QR — Gerar QR code

Fica na **roda de ações**: arraste **qualquer arquivo ou pasta** com
**Shift+Ctrl** e solte em **GERAR QR** (*MAKE QR* em inglês). O item arrastado só escolhe **onde** o QR é salvo: na pasta do
arquivo, ou dentro da pasta arrastada. A janela tem dois campos:

- **Nome:** o nome do arquivo do QR. Começa com o site do link
  (`github.com QR`) e acompanha o link até você escrever outro nome.
- **Link:** o link (ou qualquer texto). O botão dentro do campo cola o que
  estiver copiado; um link já copiado entra sozinho ao abrir.

**Personalizar** (abre e fecha) mostra uma prévia e:

- **Cor** do código e **Fundo** (ou **Transparente**). Com pouco contraste
  entre os dois, a janela avisa: alguns leitores não leem.
- **Tamanho:** Pequeno (~300 px), Médio (~600 px) ou Grande (~1200 px).
- **Margem:** a borda em volta do código (0 a 8 módulos; 4 é o padrão).
- **Correção:** quanto do código pode estar danificado e ainda ser lido
  (Baixa, Média, Alta, Máxima). Mais alta deixa o código mais denso.
- **Formato:** PNG ou SVG (nítido em qualquer tamanho).

A última personalização fica guardada para a próxima vez; **Restaurar**
volta ao padrão (preto no branco, médio, PNG).

**Gerar** salva `Nome.png` (ou `.svg`). Se já existir, vira
`Nome (2).png`. Com uma pasta fixa em Configurações > Comportamento, o QR
vai para ela.

**LER QR** (*READ QR* em inglês), também na roda de ações, lê o QR de uma imagem e
copia o conteúdo.

Sem arrastar nada: **Início > Gerar QR code…** salva na pasta de saída das
Configurações ou em **Downloads**.

Precisa do `qrencode` (`install.cmd` e o pacote da Microsoft Store já
trazem; no Arch, `sudo pacman -S qrencode`).
