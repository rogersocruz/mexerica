# Usando a roda

## Os gestos

Comece a arrastar um ou mais arquivos (do Explorer, do Nautilus, da área de
trabalho, de um diálogo de arquivos) e, **sem soltar o botão**, segure:

| Tecla | Roda | Exemplos |
|---|---|---|
| **Shift** | **Converter** | JPG, PNG, WEBP, MP4, MP3, PDF, DOCX, ZIP… |
| **Shift + Alt** | **Ferramentas** | EDIT, CROP, ADD BG, REMOVE BG, COMPRESS, TRIM… |
| **Shift + Ctrl** | **Ações** | COPY PATH, TERMINAL, COPY TO, MOVE TO, FLOAT, ZIP |

A roda aparece em volta do ponteiro. **Solte o arquivo sobre um item** para
executar. Para desistir: solte no miolo, fora da roda, ou solte o Shift
(a roda some e o arraste continua normal). **Esc** cancela o arraste
inteiro.

Dá para trocar de roda sem soltar o arquivo: com Shift pressionado, aperte
ou solte Alt/Ctrl. A roda fica no mesmo lugar.

O miolo mostra o tamanho do arquivo e, com o ponteiro sobre um item, o nome
dele. Os rótulos das ferramentas e ações ficam em inglês e caixa-alta, com um
ícone de linha.

## O que aparece

- Só os itens que servem para **todos** os arquivos arrastados. Uma imagem e
  um vídeo juntos, por exemplo, só mostram o que serve para os dois (como
  STRIP META).
- Só os itens cujo programa está instalado (veja `mexerica doctor` ou
  **Configurações > Sobre**).
- Só os itens ligados em **Configurações > Itens da roda**.
- Com vários arquivos aparecem as operações de lote (juntar PDFs, colagem,
  juntar vídeos…).
- Até 10 itens a roda tem um anel; com mais, um segundo anel por fora.

A lista completa está em [Operações](Operacoes.md).

## Regras que valem para todas as operações

- **Nunca sobrescreve.** Se o nome já existe, vira `foto (2).jpg`.
- **Nomes em inglês que se encadeiam**: `foto Cropped.jpg`,
  `foto Cropped With Background.png`. Conversão pura só troca a extensão.
- **Sem arquivo pela metade.** O resultado é gravado primeiro numa pasta
  temporária oculta, na mesma pasta, e só vira o nome final quando termina.
  Se falhar, nada fica para trás.
- **Onde salva:** ao lado do original, ou numa pasta fixa escolhida em
  [Configurações](Configuracoes.md). Se a pasta não aceitar escrita, vai para
  `Downloads`.
- **Lote:** com vários arquivos, processa todos.
- **Avisos:** uma notificação no início (pode ser desligada) e outra no fim,
  com **Mostrar na pasta** e **Abrir**. No GNOME são notificações do sistema;
  no Windows aparecem no canto da tela, no vidro das janelas da Mexerica.
  Falhas trazem **Ver log**.

## Janelas

Alguns itens (EDIT, CROP, ADD BG, RESIZE, TRIM, PAGES) abrem uma janela
antes de executar; eles ficam no topo da roda de ferramentas. Veja
[Janelas de edição](Janelas-de-edicao.md). FLOAT abre a
[bolha flutuante](Flutuar.md).

## Sem arrastar

A roda também abre por D-Bus (útil para testar), e aí o clique escolhe:

```bash
gapplication action io.github.rogersocruz.Mexerica show \
    "('convert', ['file:///caminho/foto.png'], 600, 400)"
```

Fora de um arraste, setas, Enter e Esc também funcionam. A mesma coisa sem
roda, pela [linha de comando](Linha-de-comando.md): `mexerica run to-jpg foto.png`.
