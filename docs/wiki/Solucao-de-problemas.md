# Solução de problemas

Primeiro, dois diagnósticos:

- `mexerica doctor` (ou **Configurações > Sobre**): quais programas foram
  encontrados e quem converte os documentos do Office.
- O **log** (**Configurações > Sobre > Abrir o log**, ou o menu da bandeja):
  - Windows: `%LOCALAPPDATA%\Mexerica\cache\mexerica.log`
  - Linux: `~/.cache/mexerica/mexerica.log`; a extensão:
    `journalctl --user -f -o cat /usr/bin/gnome-shell`

## A roda não abre

- **O ícone da Mexerica está na bandeja / barra superior?** Se não, o serviço
  não está rodando: abra "Mexerica" no menu Iniciar / de apps.
- **GNOME:** depois de instalar, é preciso **sair e entrar** na sessão. Veja
  o estado da extensão em **Configurações > Sobre**.
- **Windows, arrastando de um programa que não é o Explorer:** a roda só
  abre em arrastes do shell (Explorer, área de trabalho, diálogos de arquivo
  e apps que usam a imagem de arraste do Windows, como os navegadores).
- **Windows, serviço como administrador:** o Windows bloqueia o arraste de
  um programa comum para um elevado. Reinstale sem "Executar como
  administrador".
- **A roda abre e some depois de ~1 s:** o arraste não trouxe arquivos para
  a roda. O log diz "arraste sem arquivos para a roda; desistindo".
- **Uma opção esperada não aparece:** o programa dela pode faltar
  (`mexerica doctor`), ela pode não servir para todos os arquivos
  arrastados, ou foi desligada em **Configurações > Itens da roda**.

## Shift+Alt ou Shift+Ctrl troca o teclado

São os atalhos de troca de teclado do sistema. Windows: o instalador os
desliga (`.\windows-hotkeys.ps1`; troque de teclado com Win+Espaço). GNOME:
remova a opção xkb `grp:alt_shift_toggle` (veja
[Instalação no Linux](Instalacao-Linux.md)).

## Instalação no Windows

- **"a execução de scripts foi desabilitada":** use `install.cmd` em vez do
  `install.ps1` (veja [Instalação no Windows](Instalacao-Windows.md)).
- **"Rode sem Executar como administrador":** abra um terminal comum.
- **"MSYS2 não encontrado" / download falhou:** instale o MSYS2 em
  `C:\msys64` (https://www.msys2.org) e rode de novo; ou defina
  `MSYS2_ROOT` se ele estiver em outra pasta.
- **O comando `mexerica` não existe:** abra um terminal novo (o PATH muda só
  para os terminais abertos depois).

## Documentos do Office

- **O Word/Excel demora na primeira conversão:** o Office leva uns segundos
  para iniciar escondido; as seguintes são mais rápidas.
- **"o word não respondeu em 300 s":** o Office travou (por exemplo, numa
  pergunta). A Mexerica encerra só o Office que ela abriu. Tente de novo; se
  repetir, abra o arquivo no Office para ver o que ele pergunta.
- **Documento protegido por senha:** a conversão falha de propósito (não há
  como digitar a senha numa janela invisível).

## Metadados com nome acentuado

Corrigido: o exiftool recebe os argumentos em UTF-8. Se aparecer `?` no
lugar de acentos em algum outro texto, é um programa que escreve em ANSI no
Windows; o resultado é o mesmo, só o texto exibido perde o acento.

## Conhecidos

- *TRIM* não toca o vídeo, só mostra quadros; o botão de ouvir toca o áudio.
- "Juntar vídeos" pressupõe arquivos com a mesma resolução.
- Ainda não dá para tarjar ou borrar áreas de uma imagem.
- No GNOME, escala fracionária com layout físico (configuração antiga do
  Mutter) pode deslocar a roda alguns pixels do ponteiro.
