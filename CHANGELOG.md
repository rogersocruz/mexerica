# Mudanças

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e as versões, o [versionamento semântico](https://semver.org/lang/pt-BR/):
**MAIOR.MENOR.CORREÇÃO**. Funcionalidade nova sobe a MENOR; só correção, a
CORREÇÃO. Na Microsoft Store a mesma versão ganha um `.0` no fim
(`0.2.0` → `0.2.0.0`). Como fazer um lançamento:
[Desenvolvimento](docs/wiki/Desenvolvimento.md#versões).

## [0.2.0] — não lançada

### Novo

- **Juntar PDFs página a página (JUNTAR):** com 2 ou mais PDFs, a roda de
  ferramentas abre todas as páginas de todos os arquivos numa grade, na
  ordem em que os arquivos aparecem na lista do Explorer (no Windows, lida
  da própria janela; sem ela, por nome). Arraste páginas para reordenar,
  gire (↺/↻, R), apague (✕, Delete), inverta e desfaça (Ctrl+Z); cada
  página mostra de que arquivo veio. Gera um PDF só.
- **Organizar páginas (PAGES):** o mesmo organizador para um PDF:
  reordenar, girar e apagar páginas (Save) ou tirar as selecionadas para
  um PDF novo (Extract selected).
- **Dividir PDF (SPLIT):** página a página, um intervalo (sai um PDF solto),
  vários intervalos (`1-3, 4-8, 9-`, ou clicando onde começa cada arquivo)
  ou a cada N páginas.
- **Desbloquear PDF (UNLOCK):** tira a senha de abertura (pedindo a senha)
  e as restrições de imprimir, copiar e editar. A senha vai só para o
  `qpdf`, pela entrada padrão.
- **Qualidade por formato de imagem:** sliders para WEBP (com opção sem
  perda), AVIF, HEIC e JPEG XL, além do JPG, e a compressão do PNG
  (Configurações > Comportamento).
- **Desfoque configurável:** Sistema, Próprio ou Desligado, com
  intensidade. O *Próprio* (Windows) fotografa o monitor e borra em memória,
  e funciona mesmo com a transparência do Windows desligada; no GNOME a
  intensidade vale para o borrão do Shell.
- **Windows: Ctrl + botão direito** no Explorer abre a roda de ações no
  ponteiro, com os arquivos selecionados, no lugar do menu
  (Configurações > Comportamento, desligado por padrão). Tab passa para
  as rodas de conversão e de ferramentas; Shift+Tab volta. Ligada, ela
  substitui o Shift + arrastar, que deixa de abrir a roda.
- **`mexerica wheel`:** abre a roda no ponteiro pela linha de comando (com
  arquivos, o clique escolhe; sem, ela espera o arraste).
- **COSMIC e outros desktops sem a extensão do GNOME:** a roda abre por um
  atalho de teclado (`mexerica wheel`), numa camada overlay quando o
  gtk4-layer-shell está instalado.
- **Gerar QR code (MAKE QR), na roda de ações:** arraste qualquer
  arquivo ou pasta (ele só define onde salvar) e preencha **Nome** e
  **Link**; o campo do link tem um botão para colar. **Personalizar**: cor,
  fundo (ou transparente), tamanho, margem, correção de erros e PNG ou
  SVG, com prévia; a última escolha fica guardada. Também na Início, em
  **Gerar QR code…**. Usa o `qrencode`.
- **Ler QR** passou da roda de ferramentas para a de ações, junto do
  Gerar.
- Atalhos de internet (`.url` e `.webloc`) passam a ser reconhecidos.
- **Pague me um café** em Configurações > Sobre.
- **Windows: "Mexerica" no Gerenciador de Tarefas**, com o ícone dela, em
  vez de "Python": o serviço roda num `mexerica-app.exe` (o pythonw do
  MSYS2 com o nome e o ícone da Mexerica), refeito a cada instalação.
- **Formatos extras** (Configurações > Sobre): Baixar ou Remover o suporte
  a cada tipo de arquivo (vídeo, PDF, HEIC, e-books, fontes…). Instala pelo
  MSYS2/winget no Windows e pelo apt/dnf/pacman no Linux; nunca remove o
  que outro programa usa.
- **Textos das Configurações reescritos:** mais curtos e diretos, sem citar
  o sistema. O Sobre ficou só com o que importa (sem a lista de programas,
  caminhos do log e das configurações; isso continua no `mexerica
  doctor`).
- **Português ou inglês:** Configurações > Aparência > Idioma. Em
  *Sistema* (padrão), português se o sistema estiver em português e inglês
  em qualquer outro idioma. Vale para tudo o que aparece: janelas, roda,
  avisos, bandeja, menu do GNOME e linha de comando. As janelas de edição,
  que eram só em inglês, ficam em português.
- **Organizador de páginas com arraste ao vivo:** as outras páginas abrem
  espaço enquanto você arrasta; soltar confirma, Esc volta.
- README: como a IA é usada no desenvolvimento; `CONTRIBUTING.md` e modelo
  de pull request com as regras para aceitar PRs.

### Mudou

- **Um Juntar só:** o que abre a tela com as páginas. O juntar direto, sem
  tela (`pdf-merge`), saiu da roda, da Início e da linha de comando.
- **Dividir** em um PDF por página saiu da roda por padrão (o SPLIT faz
  isso com "Single pages"). Continua em Configurações > Itens da roda, na
  Início e em `mexerica run pdf-split`.

### Corrigido

- **Tela preta no Windows** ao abrir a roda (o monitor inteiro) e janelas
  escuras, quando os *Efeitos de transparência* estão desligados ou a
  **Economia de energia** está ligada (notebook na bateria). Sem a
  transparência do Windows, a roda fica sem borrão (ou com o desfoque
  próprio) e as janelas ganham fundo sólido. (Era a 0.1.2, que não chegou
  a ser publicada.)
- **Aparência que não ficava gravada:** um slider arrastado regravava o
  arquivo de configurações a cada passo e, no Windows, a gravação falhava
  com o arquivo ocupado (antivírus, indexador) e a mudança se perdia. Agora
  vale na hora, grava um instante depois e tenta de novo se o arquivo
  estiver ocupado. Números gravados como `40.0` também passam a valer.
- Janelas abertas (edição, Flutuar) passam a mudar de estilo na hora.
- A opacidade das janelas aparece apagada, com o motivo, quando a
  transparência do Windows está desligada (ela não teria efeito).
- SVG → JPG ignorava a qualidade escolhida.
- **Windows: caminhos com "/"** quebravam o que passa pelo shell: arrastar
  da bolha Flutuar, ícones e nomes como o Explorer mostra, Mostrar na pasta
  e conversões de planilha pelo Excel ("mesmo nome de uma pasta aberta").
  Os caminhos agora vão com "\\" para o Windows.
- **Escolher cor** (Gerar QR code e Adicionar fundo > Outra cor): a janela
  de cores abria atrás da janela de edição e não dava para usar. Agora a
  escolha abre na própria janela: paleta e código #RRGGBB.

## [0.1.1] — 2026-11-09

Primeira versão publicada na Microsoft Store.

### Mudou

- Versão da Store: os atalhos Alt+Shift / Ctrl+Shift do Windows são
  desligados nas Configurações do Windows (Teclado avançado), que o app
  abre. O pacote não pede mais `unvirtualizedResources`.

## [0.1.0] — 2026-11-06

Primeira versão: rodas de conversão, ferramentas e ações; janelas de
edição de imagem, vídeo, áudio e PDF; Início, Flutuar, menu de contexto;
instalação por script no Windows e no Arch (GNOME).

[0.2.0]: https://github.com/rogersocruz/mexerica/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/rogersocruz/mexerica/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/rogersocruz/mexerica/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rogersocruz/mexerica/releases/tag/v0.1.0
