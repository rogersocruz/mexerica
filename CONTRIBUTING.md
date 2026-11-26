# Contribuindo com a Mexerica

Obrigado pelo interesse! Este guia diz o que um pull request precisa ter
para ser aceito. Como rodar e testar o projeto está em
[Desenvolvimento](docs/wiki/Desenvolvimento.md).

## Antes de começar

- Para algo maior que uma correção pequena, **abra uma issue antes** e
  descreva a ideia. Evita trabalho que não vai entrar (por exemplo, algo
  que precise de rede ou de um serviço externo).
- Um PR resolve **uma coisa**. Correção e funcionalidade nova vão em PRs
  separados.

## O que todo PR precisa ter

1. **Testes passando:** `make test` (ou, no Windows,
   `C:\msys64\ucrt64\bin\python.exe -m pytest -q tests` e
   `node tests\extension_logic.test.mjs`). Testes que dependem de um
   programa ausente são pulados sozinhos; diga no PR quais rodaram.
2. **Teste novo** para o que mudou no motor (`mexerica/engine`): uma
   operação nova precisa de pelo menos um teste que rode o programa de
   verdade.
3. **Testado de verdade:** descreva onde você experimentou (GNOME/versão,
   Windows 10/11) e como. Mudanças na roda, nas janelas ou no arraste não
   têm teste automático que baste.
4. **CHANGELOG:** uma linha em [CHANGELOG.md](CHANGELOG.md), na versão
   ainda não lançada, no formato que já está lá.
5. **Docs:** se mudou algo visível, atualize a página da
   [wiki](docs/wiki/Home.md) correspondente (e
   `python docs/gerar_operacoes.py` se mexeu nas operações).

## Regras do projeto

- **100% local.** Nada de rede, telemetria, download em tempo de execução
  ou serviço externo ([PRIVACY.md](PRIVACY.md)).
- **Nunca estragar um arquivo:** não sobrescrever o original, gravar num
  temporário e só mover no fim (o `runner` já faz isso; use-o).
- **Sem binários gerados** no PR (pacotes, builds, imagens de teste
  grandes). Ícones e capturas da documentação são exceção.
- Programas externos são **opcionais**: a operação declara o que precisa
  em `needs` e some da roda quando falta.
- Código e comentários em português, como o resto do projeto.
- **Texto que aparece para o usuário** é escrito em português e passa por
  `_()` (de `mexerica/i18n.py`); a tradução inglesa vai em
  `mexerica/i18n_en.py`. `python tests/i18n_strings.py` lista o que falta, e
  o `tests/test_i18n.py` falha enquanto faltar. Texto com valores:
  `_("{n} páginas").format(n=n)`, nunca f-string dentro do `_()`.

## Uso de IA

Usar um assistente de IA para escrever código é permitido (o próprio
projeto usa: veja o README). Mas:

- **Diga no PR** se usou IA e em que parte (código, testes, texto).
  Commits com `Co-Authored-By:` também servem.
- **Você responde pelo PR:** leia e entenda cada linha antes de enviar.
  PR com código que o autor não sabe explicar, testes que não rodam ou
  descrição genérica será fechado.
- Não cole no assistente arquivos, logs ou dados de outras pessoas.

## Revisão

O mantenedor revisa assim que der. Pedidos de mudança são normais; responda
no próprio PR. PRs parados por mais de 30 dias sem resposta do autor podem
ser fechados (dá para reabrir).
