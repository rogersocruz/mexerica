# Desenvolvimento

## Testes

```bash
make test        # pytest + teste da extensão (node)
```

No Windows, com o Python do MSYS2 (é o que tem GTK, cairo e os conversores):

```powershell
C:\msys64\ucrt64\bin\python.exe -m pytest -q tests
node tests\extension_logic.test.mjs
```

- Os testes do motor rodam os programas de verdade e **se pulam** quando o
  programa falta, então a suíte roda em qualquer máquina.
- `tests/conftest.py` dá a cada teste configurações próprias: nada lê ou
  grava as suas.
- `tests/test_drag.py`: a regra de abrir/fechar a roda (Windows), sem mouse.
- `tests/test_win32.py`: bandeja, objeto de arraste, ícones do Explorer (só
  no Windows).
- `tests/test_office.py`: quem converte cada documento, sem rodar nada; e,
  havendo Microsoft Office, Word/Excel/PowerPoint de verdade.
- `tests/extension_logic.test.mjs`: a extensão do GNOME com mocks (arraste,
  coordenadas, vidro, ícone na barra superior, configurações).

## Rodar sem instalar

```bash
python -m mexerica            # o serviço (precisa do GTK 4)
python -m mexerica run to-jpg foto.png
```

No Windows, para atualizar a cópia instalada a partir do repositório:
`.\install.cmd -AppOnly`.

## Acrescentar uma operação

Declare um `Op` em `mexerica/engine/ops.py`:

```python
Op("img-sepia", "Sépia", TOOLS, frozenset({F.IMAGE}),
   _img_tool("-sepia-tone", "80%"), suffix=" Sepia", needs=("magick",),
   hint="Tom sépia")
```

- os tipos de entrada que aceita, os programas de que precisa (`needs`) e um
  `build(ctx)` que devolve os passos: listas de argumentos (rodam como
  subprocesso) ou funções `f(ctx)`;
- ela aparece sozinha na roda certa, nas [Configurações](Configuracoes.md) e
  na linha de comando; o rótulo e o ícone da roda ficam em `theme.LABELS` e
  `theme.ICONS`;
- grave sempre em `ctx.out` (o runner cuida do nome final, de nunca
  sobrescrever e do temporário);
- regenere a página [Operações](Operacoes.md) da wiki:
  `python docs/gerar_operacoes.py`.

## Acrescentar um estilo

Uma entrada em `theme.STYLES` (cores do acento, do miolo, do texto, do
gradiente das janelas e do vidro da roda). Ela aparece sozinha em
**Configurações > Aparência**.

## Mexer na extensão do GNOME

`extension/mexerica@rogersocruz.github.io/extension.js`. No Wayland o Shell
só recarrega uma extensão no login; o teste com mocks
(`tests/extension_logic.test.mjs`) cobre a lógica sem precisar do GNOME.

## Estrutura

Veja [Como funciona](Como-funciona.md). Resumo:

```
mexerica/
  app.py              serviço GTK: roda, trabalhos, notificações
  settings.py         configurações (JSON)        settings_window.py  a janela
  floating.py         Flutuar                     theme.py            estilos e CSS
  wheel/              geometria e desenho da roda
  editors/            janelas de edição
  engine/             motor: formatos, operações, runner, Office
  desktop/            GNOME, Windows (win32.py, drag.py, toast.py)
  data/               ícones usados pela bandeja e pelo Sobre
extension/            extensão do GNOME Shell
docs/wiki/            esta wiki
install.sh, install.ps1/.cmd, uninstall.*, windows-hotkeys.ps1
```
