# Configurações

Abra pelo **menu de apps / menu Iniciar** ("Mexerica"), clicando no
[ícone da bandeja ou da barra superior](Bandeja-e-barra-superior.md), ou
rodando `mexerica` sem argumentos. **Tudo vale na hora** e fica gravado: não
há botão de salvar.

## Aparência

No topo, uma **prévia da roda** de verdade, que muda junto com as opções.

| Opção | O que muda |
|---|---|
| **Idioma** | **Automático** (padrão): português se o Windows ou o Linux estiver em português, inglês em qualquer outro idioma. Ou escolha **Português** ou **English**. Vale para as janelas, a roda, os avisos, a bandeja, o menu da barra superior do GNOME e a linha de comando; a janela de Configurações se refaz na hora |
| **Cores** | As cores da roda e das janelas: **Mexerica** (laranja, o original), **Oceano** (azul), **Menta** (verde), **Uva** (roxo) e **Grafite** (escuro, acento laranja) |
| **Tamanho da roda** | Pequena, Média ou Grande |
| **Escurecer a tela** | Quanto a tela atrás da roda escurece (0–60%). Vale no Windows e no GNOME |
| **Opacidade das janelas** | Das janelas de edição e das notificações do Windows (60–100%). No Windows com a transparência desligada (ou a Economia de energia ligada) as janelas ficam sólidas e o slider fica apagado |
| **Animações** | Entrada da roda, hover e troca de roda. Desligadas, tudo aparece de uma vez |
| **Tipo de desfoque** | O desfoque de fundo atrás da roda. **Do sistema:** o borrão do Windows (DWM) ou do GNOME Shell. **Próprio:** a Mexerica fotografa o monitor antes de a roda aparecer e borra a imagem em memória (nada é gravado); funciona mesmo com a transparência do Windows desligada. **Desligado:** só o escurecimento |
| **Intensidade do desfoque** | 0–40 px. Vale para o desfoque próprio e para o do GNOME |

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
| **Onde salvar** | *Na mesma pasta do arquivo original* (padrão) ou *Sempre nesta pasta*. Se a pasta escolhida sumir, volta a salvar ao lado do original |
| **Qualidade das imagens** | Um slider por formato nas conversões da roda e do Início: **JPG** (padrão 92), **WEBP** (85, ou *sem perda*), **AVIF** (60), **HEIC** (70) e **JPEG XL** (85), mais a **compressão do PNG** (0–9, sem perda: só troca tamanho por tempo). O *Editar…*, o *Tamanho…* e o *Comprimir* têm a própria |
| **Avisar quando uma conversão começa** | Desligado, só aparece o aviso de conclusão (com Mostrar na pasta) |
| **Abrir ao entrar no sistema** | Sobe a Mexerica no login. No Windows, guarda o atalho da pasta Inicializar fora dela; no GNOME, grava a escolha em `~/.config/autostart` |
| **Roda com Ctrl + botão direito** (Windows) | No Explorer e na área de trabalho, **Ctrl + botão direito** sobre arquivos selecionados abre a [roda de ações](Usando-a-roda.md#por-clique) no lugar do menu. **Tab** passa para a próxima roda (conversão, ferramentas, ações) e **Shift+Tab** volta; **Esc** fecha. **Substitui o Shift + arrastar:** com a opção ligada, arrastar segurando Shift não abre mais a roda (os dois não convivem). Sem o Ctrl, o botão direito abre o menu de sempre |

## Sobre

Versão, o botão **Pague me um café** (abre
[buymeacoffee.com/rogersocruz](https://buymeacoffee.com/rogersocruz) no
navegador), os atalhos durante o arraste e **Sair da Mexerica**. Um aviso
aparece só se a detecção de arraste estiver desligada.

### Formatos extras

Uma linha por tipo de arquivo (Imagens, HEIC e AVIF, SVG, Vídeo e áudio,
PDF, Documentos e Markdown, Documentos do Office, E-books, Metadados, QR
code, Compactados, Dados, Fontes), com **Instalado** e um botão:

- **Baixar** instala os programas daquele tipo; os itens dele aparecem na
  roda na hora.
- **Remover** pede confirmação e desinstala; os itens somem da roda.
  Nunca remove o que outro programa usa: nesse caso avisa e não mexe.

Como instala: no Windows, pelo MSYS2 (`pacman`) e pelo `winget` (Pandoc,
ExifTool, LibreOffice, calibre), sem administrador. No Linux, pelo `apt`,
`dnf` ou `pacman`, pedindo a senha (`pkexec`); no `dnf` só dá para
instalar. Na versão da Microsoft Store os formatos já vêm incluídos.
O que foi encontrado nesta máquina, com o caminho de cada programa:
`mexerica doctor`.

As mudanças valem na hora; o arquivo é gravado um instante depois da última
(um slider arrastado não regrava o arquivo a cada passo). Se o arquivo
estiver ocupado por outro programa, a Mexerica tenta de novo e a mudança
continua valendo.

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
