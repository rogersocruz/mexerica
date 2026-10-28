# Configurações

Abra pelo **menu de apps / menu Iniciar** ("Mexerica"), clicando no
[ícone da bandeja ou da barra superior](Bandeja-e-barra-superior.md), ou
rodando `mexerica` sem argumentos. **Tudo vale na hora** e fica gravado: não
há botão de salvar.

## Aparência

No topo, uma **prévia da roda** de verdade, que muda junto com as opções.

| Opção | O que muda |
|---|---|
| **Estilo** | As cores da roda e das janelas: **Mexerica** (laranja, o original), **Oceano** (azul), **Menta** (verde), **Uva** (roxo) e **Grafite** (escuro, acento laranja) |
| **Tamanho da roda** | Pequena, Média ou Grande |
| **Escurecer o fundo** | Quanto a tela atrás da roda escurece (0–60%). Vale no Windows e no GNOME |
| **Opacidade das janelas** | Das janelas de edição e das notificações do Windows (60–100%) |
| **Animações** | Entrada da roda, hover e troca de roda. Desligadas, tudo aparece de uma vez |

## Itens da roda

Uma aba por roda (**Converter**, **Ferramentas**, **Ações**) e, dentro, os
itens agrupados por tipo de arquivo (Imagens, Vídeo, Áudio, PDF,
Documentos…). Cada item é uma pílula: **laranja aparece, cinza não**. Passe o
mouse para ver o que o item faz.

- Pílulas apagadas são itens cujo programa não está instalado (o motivo
  aparece ao passar o mouse). Ligadas ou não, só aparecem quando o programa
  existir.
- Alguns presets vêm **fora da roda por padrão** (≤ 1 MB, 50%, espelhar,
  P&B, ≤ 25 MB, ≤ 10 MB), porque as janelas fazem o mesmo com mais controle.
  Ligue se quiser o atalho de um clique.
- **Restaurar o padrão** desfaz tudo desta página.

Um item escondido continua disponível na [linha de comando](Linha-de-comando.md).

## Comportamento

| Opção | O que faz |
|---|---|
| **Pasta de saída** | *Ao lado do arquivo original* (padrão) ou *Sempre nesta pasta*. Se a pasta escolhida sumir, volta a salvar ao lado do original |
| **Qualidade do JPG** | Das conversões para JPG (50–100, padrão 92). O *Editar…* tem a dele |
| **Avisar quando um trabalho começa** | Desligado, só aparece o aviso de pronto (com Mostrar na pasta) |
| **Iniciar com o sistema** | Sobe a Mexerica no login. No Windows, guarda o atalho da pasta Inicializar fora dela; no GNOME, grava a escolha em `~/.config/autostart` |

## Sobre

Versão, se a detecção de arraste está ativa (no GNOME, o estado da
extensão), os gestos, os **programas encontrados** (✓ ou —, com o que cada um
faz), quem converte os documentos do Office e botões para **abrir o log**,
**abrir a pasta das configurações** e **sair da Mexerica**.

## Onde fica

Um JSON, que pode ser editado à mão (chave desconhecida ou valor de tipo
errado é ignorado):

- Windows: `%APPDATA%\Mexerica\settings.json`
- Linux: `~/.config/mexerica/settings.json`

| Chave | Padrão | Valores |
|---|---|---|
| `style` | `"mexerica"` | `mexerica`, `oceano`, `menta`, `uva`, `grafite` |
| `wheel_size` | `"medium"` | `small`, `medium`, `large` |
| `window_opacity` | `92` | 60–100 |
| `dim` | `28` | 0–60 (a extensão do GNOME também lê) |
| `animations` | `true` | |
| `hidden` | `[]` | ids de operações tiradas da roda |
| `extra` | `[]` | ids de presets postos na roda |
| `output` | `"beside"` | `beside`, `folder` |
| `output_folder` | `""` | caminho da pasta |
| `jpeg_quality` | `92` | 50–100 |
| `notify_start` | `true` | |

Os ids estão em [Operações](Operacoes.md). O motor e a linha de comando leem o
mesmo arquivo (a pasta de saída e a qualidade do JPG valem também no
`mexerica run`).
