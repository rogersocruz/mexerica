# Mudanças

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e as versões, o [versionamento semântico](https://semver.org/lang/pt-BR/):
**MAIOR.MENOR.CORREÇÃO**. Funcionalidade nova sobe a MENOR; só correção, a
CORREÇÃO. Na Microsoft Store a mesma versão ganha um `.0` no fim
(`0.2.0` → `0.2.0.0`). Como fazer um lançamento:
[Desenvolvimento](docs/wiki/Desenvolvimento.md#versões).

## [0.2.0] — não lançada

### Novo

- **Juntar PDFs na ordem escolhida (MERGE…):** a roda de ferramentas, com
  vários PDFs, abre uma lista na ordem da seleção, com a primeira página de
  cada um. Arraste para reordenar (ou Alt+↑/↓), tire arquivos, ordene de A
  a Z ou inverta. O **MERGE** de um clique continua juntando na ordem da
  seleção.
- **Dividir PDF (SPLIT):** por intervalos (`1-3, 4-8, 9-`), clicando nas
  páginas onde começa cada arquivo, ou a cada N páginas. Cada parte vira um
  PDF numa pasta.
- **Gerar QR code (MAKE QR):** para `.url`, `.webloc`, `.txt`, `.md` e
  `.html`, com os links achados no arquivo; e, na Início, **Gerar QR
  code…** para um link colado. PNG ou SVG. Usa o `qrencode`.
- Atalhos de internet (`.url` e `.webloc`) passam a ser reconhecidos.

### Mudou

- **Dividir** em um PDF por página saiu da roda por padrão (o SPLIT faz
  isso com "Every N pages" = 1). Continua em Configurações > Itens da roda,
  na Início e em `mexerica run pdf-split`.

## [0.1.2] — não lançada

### Corrigido

- **Tela preta no Windows** ao abrir a roda (o monitor inteiro) e janelas
  escuras, quando os *Efeitos de transparência* estão desligados ou a
  **Economia de energia** está ligada (notebook na bateria). O borrão do
  vidro só é ligado com a transparência do Windows ativa; sem ela, a roda
  fica sem borrão e as janelas ganham fundo sólido.

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
