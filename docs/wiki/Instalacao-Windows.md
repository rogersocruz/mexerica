# Instalação no Windows 10 e 11

A interface usa o mesmo GTK 4 do Linux, que no Windows vem do
[MSYS2](https://www.msys2.org). Basta clonar e rodar, **sem administrador**:

```powershell
git clone https://github.com/rogersocruz/mexerica
cd mexerica
.\install.cmd -Converters
```

No fim, o ícone da Mexerica aparece perto do relógio e ela já está rodando.
Não precisa sair da sessão.

## Por que `install.cmd` e não `install.ps1`

O `install.cmd` só chama o `install.ps1` com `-ExecutionPolicy Bypass`. No
padrão do Windows (política `Restricted`) um `.ps1` nem começa. Se o seu
PowerShell já aceita scripts (`RemoteSigned`), `.\install.ps1 -Converters` dá
no mesmo. Os dois aceitam as mesmas opções.

**Não rode como administrador.** A instalação é por usuário, e o serviço tem
de ficar no mesmo nível do Explorer: elevado, o Windows bloqueia o arraste do
Explorer para a roda. O instalador recusa rodar elevado.

## Opções

| Opção | O que faz |
|---|---|
| *(nenhuma)* | MSYS2 (se faltar), Python 3, GTK 4, PyGObject, pycairo e os ícones Adwaita |
| `-Converters` | Também os conversores: ffmpeg, ImageMagick, libheif, librsvg, poppler, qpdf, Ghostscript, zbar, libarchive e typst (MSYS2); Pandoc e ExifTool (winget) |
| `-Office` | LibreOffice (~350 MB, winget). Opcional: veja [Documentos do Office](Documentos-do-Office.md) |
| `-AppOnly` | Só copia o código e reinicia o serviço, sem mexer no MSYS2 (use depois de um `git pull`) |
| `-KeepLayoutHotkeys` | Não desliga os atalhos de troca de teclado (abaixo) |

A roda só mostra as opções dos programas que encontrar, então dá para
instalar menos e completar depois. Para conferir o que foi encontrado:
`mexerica doctor` ou **Configurações > Sobre**.

## O que a instalação faz

- **MSYS2:** procura em `MSYS2_ROOT`, `C:\msys64`, `%LOCALAPPDATA%\msys64` e
  no scoop. Sem ele, baixa o pacote base e extrai em `C:\msys64` (ou em
  `%LOCALAPPDATA%\msys64`, se `C:\` não aceitar), sem administrador; se o
  download falhar, tenta o winget.
- **App:** copia o código para `%LOCALAPPDATA%\Mexerica\app`.
- **Comando `mexerica`:** entra no PATH do usuário (vale nos terminais
  abertos depois da instalação).
- **Atalhos:** "Mexerica" no menu Iniciar (abre as
  [Configurações](Configuracoes.md)) e "Mexerica (serviço)" na pasta
  Inicializar (sobe o serviço no login, sem janela). Desligar "Iniciar com o
  sistema" nas Configurações guarda esse atalho fora da pasta, e o instalador
  respeita a escolha.
- **Atalhos de teclado:** veja abaixo.
- **Serviço:** reinicia o serviço; o anterior é avisado para sair pela janela
  da bandeja (assim o ícone some direito).

## Atalhos de troca de teclado (Alt+Shift e Ctrl+Shift)

Shift+Alt abre a roda de ferramentas e Shift+Ctrl a de ações. Com mais de um
teclado ou idioma instalado, o Windows usa as mesmas teclas para trocar de
teclado (Alt+Shift troca o idioma, Ctrl+Shift o layout), e cada roda aberta
trocaria o teclado junto.

Por isso o instalador desliga esses dois atalhos e **avisa no fim**. Para
trocar de teclado depois disso, use **Win+Espaço**. Quem faz isso é o
`windows-hotkeys.ps1`:

```powershell
.\windows-hotkeys.ps1            # desliga (só o que conflita)
.\windows-hotkeys.ps1 -Restore   # devolve como era
```

Ele mexe só nos atalhos que conflitam (um atalho com a tecla ` fica como
está), guarda os valores originais em
`%LOCALAPPDATA%\Mexerica\layout-hotkeys.json` e vale na hora. O desinstalador
devolve os atalhos.

## Atualizar

```powershell
git pull
.\install.cmd -AppOnly
```

## Desinstalar

```powershell
.\uninstall.cmd
```

Tira o serviço, os atalhos, o comando `mexerica` do PATH e devolve os
atalhos de teclado. O MSYS2, os conversores, o log
(`%LOCALAPPDATA%\Mexerica\cache`) e as configurações (`%APPDATA%\Mexerica`)
ficam; apague à mão se quiser.
