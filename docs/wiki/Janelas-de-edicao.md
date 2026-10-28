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
