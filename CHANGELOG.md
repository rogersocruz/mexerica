# Mudanças

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e as versões, o [versionamento semântico](https://semver.org/lang/pt-BR/):
**MAIOR.MENOR.CORREÇÃO**. Funcionalidade nova sobe a MENOR; só correção, a
CORREÇÃO. Na Microsoft Store a mesma versão ganha um `.0` no fim
(`0.1.2` → `0.1.2.0`).

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

[0.1.2]: https://github.com/rogersocruz/mexerica/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/rogersocruz/mexerica/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rogersocruz/mexerica/releases/tag/v0.1.0
