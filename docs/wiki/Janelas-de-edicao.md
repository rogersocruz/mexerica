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

### PAGES — PDF Pages

Miniaturas das páginas; selecione e escolha **extrair**, **apagar** ou
**girar** as selecionadas. **Ctrl+A** seleciona todas.

### SPLIT — Split PDF

Divide um PDF em vários, numa pasta (`relatório Parts`, com
`relatório 1-3.pdf`, `relatório 4-8.pdf`…).

- **Ranges:** escreva os trechos, como `1-3, 4-8, 9-` (`9-` vai até o fim,
  `-4` começa na primeira). Cada trecho vira um arquivo; trechos podem
  pular páginas ou se repetir.
- **Clique numa página** para começar um arquivo novo nela, como uma
  tesoura; clique de novo para desfazer. Os trechos no campo acompanham.
- **Every N pages:** um arquivo a cada N páginas (1 = um por página).
- Cada miniatura mostra a que arquivo vai; as que ficam de fora aparecem
  apagadas.

Um PDF por página sem abrir janela continua existindo (**EVERY PAGE**),
fora da roda por padrão: ligue em Configurações > Itens da roda.

### MERGE e MERGE… — juntar PDFs

Selecione vários PDFs, arraste com **Shift+Alt** e solte em:

- **MERGE:** junta na hora, **na ordem da seleção** (a ordem em que o
  Explorer ou o Nautilus entregam os arquivos).
- **MERGE…:** abre a lista na ordem da seleção, com a primeira página de
  cada arquivo. **Arraste** as linhas para mudar a ordem, ou use as setas
  (**Alt+↑/↓**). **×** (ou **Delete**) tira um arquivo; **A–Z**, **Reverse**
  e **Selection order** reordenam de uma vez.

O resultado leva o nome do primeiro arquivo da lista com o sufixo
`Merged`.

## Texto e links

### MAKE QR — QR Code

Para `.url` (atalho de internet do Windows), `.webloc` (do Mac), `.txt`,
`.md` e `.html`: a janela acha os links do arquivo e mostra o QR do
primeiro. Com mais de um link, escolha na lista; ou cole outro no campo
(botão ao lado, ou **Ctrl+V**). Sai em **PNG** ou **SVG**, ao lado do
arquivo (`Site QR.png`).

Sem arquivo: **Início > Gerar QR code…**. Se houver um link copiado, ele já
aparece; o QR vai para a pasta de saída das Configurações ou para
**Downloads**, com o nome do site (`github.com QR.png`).

Precisa do `qrencode` (`install.cmd` e o pacote da Microsoft Store já
trazem; no Arch, `sudo pacman -S qrencode`).
