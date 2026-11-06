# Mexerica na Microsoft Store

Esta pasta gera o pacote **MSIX** da Mexerica e reúne o que a Microsoft
Store pede no envio. O pacote é autocontido: leva o Python, o GTK 4 e
todos os conversores (ffmpeg, ImageMagick, Ghostscript, poppler, qpdf,
pandoc, typst, exiftool…). Quem instala pela Store não precisa de MSYS2,
winget nem script.

| Arquivo | Para quê |
|---|---|
| [build.ps1](build.ps1) | gera `dist\Mexerica_<versão>_x64.msix` |
| [stage.py](stage.py) | monta a pasta do pacote (runtime do MSYS2, app, logos, manifesto, avisos de licença) |
| [AppxManifest.xml.in](AppxManifest.xml.in) | manifesto do pacote (o stage.py preenche) |
| [launcher.cs](launcher.cs) | os três `.exe` do pacote (menu Iniciar, serviço no login, comando `mexerica`) |
| [store.json](store.json) | identidade do pacote (vem do Partner Center) |
| [listing.md](listing.md) | textos da página na Store, prontos para colar |
| [../../PRIVACY.md](../../PRIVACY.md) | política de privacidade (a Store pede a URL) |

## Como o pacote funciona

- **Menu Iniciar:** `Mexerica.exe` abre a janela Início.
- **Login:** a *StartupTask* do pacote sobe o `MexericaService.exe`
  (serviço da roda). Se o usuário desligar "Iniciar com o sistema" nas
  Configurações, o serviço sai logo ao subir. Também dá para desligar em
  Configurações do Windows > Aplicativos > Inicialização.
- **Botão direito:** "Converter com a Mexerica" para as extensões que a
  Mexerica conhece (em "Mostrar mais opções" no Windows 11). Pastas não
  entram: o MSIX só registra verbos por extensão.
- **Terminal:** o alias `mexerica` (`mexerica doctor`, `mexerica run …`).
- **Atalhos Alt+Shift / Ctrl+Shift:** nada roda na instalação. Na primeira
  vez que o serviço sobe, um aviso oferece desligar esses atalhos do
  Windows. Também há a chave "Liberar Shift+Alt e Shift+Ctrl" nas
  Configurações. Os originais ficam no mesmo JSON do
  `windows-hotkeys.ps1`.
- **Sem virtualização** (`unvirtualizedResources`): configurações, cache
  e registro ficam nos lugares de sempre (`%APPDATA%\Mexerica`,
  `%LOCALAPPDATA%\Mexerica`). Assim o Office, que roda fora do pacote, vê
  os mesmos arquivos, e a mudança dos atalhos de teclado vale no sistema.

> **Não instale as duas versões juntas.** Antes de testar o MSIX, rode o
> `uninstall.cmd` da instalação por script. Se as duas estiverem
> instaladas, só o primeiro serviço que subir fica rodando.

## 1. Pré-requisitos (uma vez)

1. **MSYS2** em `C:\msys64`. O `install.cmd` da raiz já instala; ou
   baixe em <https://www.msys2.org>.
2. **Windows SDK** (makeappx, makepri, signtool, App Certification Kit):

   ```powershell
   winget install Microsoft.WindowsSDK.10.0.26100
   ```

3. **Conta no Partner Center:** <https://partner.microsoft.com/dashboard>
   > Inscrever-se como desenvolvedor de **pessoa física** (individual). A
   conta individual é gratuita.

## 2. Reservar o nome e pegar a identidade

1. Partner Center > **Aplicativos e jogos** > **Novo produto** >
   **Aplicativo MSIX ou PWA** > reserve o nome **Mexerica**.
2. No produto, abra **Gerenciamento de produto > Identidade do produto** e
   copie para o [store.json](store.json):

   | Partner Center | store.json |
   |---|---|
   | `Package/Identity/Name` (ex.: `12345RogerCruz.Mexerica`) | `identityName` |
   | `Package/Identity/Publisher` (ex.: `CN=1A2B3C4D-…`) | `publisher` |
   | `Package/Properties/PublisherDisplayName` | `publisherDisplayName` |

   Enquanto o store.json tiver a identidade de teste
   (`io.github.rogersocruz.Mexerica`), o build avisa. Ela serve para
   testar nesta máquina, mas a Store recusa o pacote com ela.

## 3. Gerar o pacote

```powershell
cd packaging\msstore
.\build.ps1                # atualiza o MSYS2 e gera dist\Mexerica_0.1.0.0_x64.msix
.\build.ps1 -SkipUpdate    # sem rodar o pacman (mais rápido)
.\build.ps1 -Version 0.1.1.0
```

- A versão vem de `__version__` em `mexerica/__init__.py` + `.0`. **Cada
  envio precisa de uma versão maior** que a anterior, e o último número
  tem de ser 0.
- O build confere se todas as DLLs importadas estão no pacote. DLL de
  plugin opcional cuja dependência não está instalada (frei0r com
  OpenCV, o coder DOT do graphviz…) sai do pacote, e o build lista o que
  saiu.
- O pandoc e o exiftool são baixados (versões fixas no `stage.py`) e
  ficam em cache em `build\downloads`.
- Tamanho atual: cerca de 340 MB compactado e 1 GB instalado.

## 4. Testar nesta máquina

**Jeito rápido (sem certificado):** ligue o *Modo de desenvolvedor*
(Configurações > Sistema > Para desenvolvedores) e registre a pasta do
pacote:

```powershell
Add-AppxPackage -Register .\build\stage\AppxManifest.xml
# remover:
Get-AppxPackage *Mexerica* | Remove-AppxPackage
```

**O .msix de verdade:** gere com `-Sign`, confie no certificado de teste
uma vez (PowerShell **como administrador**) e instale com dois cliques:

```powershell
.\build.ps1 -SkipUpdate -Sign
# como administrador:
Import-Certificate -FilePath .\dist\Mexerica-teste.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople
```

Roteiro de teste:

- [ ] Arraste um arquivo no Explorer segurando Shift, depois Shift+Alt e
      Shift+Ctrl: as três rodas abrem e convertem.
- [ ] O aviso dos atalhos de teclado aparece uma vez e "Desligar atalhos"
      funciona (com dois teclados instalados, Shift+Alt não troca mais o
      teclado).
- [ ] O botão direito > Mostrar mais opções > "Converter com a Mexerica"
      abre a janela Início com o arquivo.
- [ ] `mexerica doctor` num terminal novo lista tudo como `ok`, menos
      rembg e ebook-convert, que são opcionais e ficam fora do pacote.
- [ ] Saia da sessão e entre de novo: o ícone volta para a bandeja.
      Desligue "Iniciar com o sistema", repita e confira que não volta.
- [ ] Converta um DOCX com o Word instalado (COM fora do pacote).
- [ ] Desinstale pelo menu Iniciar e confira que nada fica rodando.

## 5. Windows App Certification Kit (antes de enviar)

O mesmo teste que a Store roda na certificação. PowerShell **como
administrador**:

```powershell
$wack = "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit\appcert.exe"
& $wack reset
& $wack test -appxpackagepath .\dist\Mexerica_0.1.0.0_x64.msix -reportoutputpath .\dist\wack.xml
```

## 6. Enviar

Partner Center > Mexerica > **Iniciar envio**:

1. **Preços e disponibilidade:** Gratuito; todos os mercados (ou só
   Brasil e Portugal, se quiser começar por eles); visibilidade pública.
2. **Propriedades:** categoria *Produtividade*. Em "Este produto acessa,
   coleta ou transmite informações pessoais?": **Não**. Política de
   privacidade: `https://github.com/rogersocruz/mexerica/blob/main/PRIVACY.md`.
   Site e suporte: veja o [listing.md](listing.md).
3. **Classificações etárias:** questionário da IARC. Tipo de app:
   utilitário/produtividade. Responda **não** a violência, conteúdo
   sexual, apostas, compras e interação entre usuários. Resultado
   esperado: Livre (L/3+).
4. **Pacotes:** arraste o `dist\Mexerica_<versão>_x64.msix`. Use o
   **sem** `-Sign`: a Store assina com o certificado dela. Família de
   dispositivos: só *Desktop*.
5. **Listagens da Store > Português (Brasil):** cole os textos do
   [listing.md](listing.md) e envie as capturas de tela (mínimo
   1366 × 768).
6. **Opções de envio > Notas para a certificação**, em inglês, porque
   os testadores leem em inglês:

   ```text
   How to test: open File Explorer, start dragging any image file and hold
   Shift while dragging. A wheel of formats appears around the pointer;
   drop the file on "PNG" to get a converted copy next to the original.
   Shift+Alt shows tools, Shift+Ctrl shows actions. The background service
   starts with Windows (StartupTask) and shows a tray icon; the Start menu
   entry opens the main window. No account or network access is needed.
   ```

7. **Justificativa das funcionalidades restritas** (campo que aparece
   por causa do `runFullTrust` e do `unvirtualizedResources`):

   ```text
   runFullTrust: Mexerica is a desktop (Win32) file converter built with
   GTK 4 and Python. It watches the Explorer drag-and-drop gesture (mouse
   button + Shift/Alt/Ctrl) to show its wheel and runs bundled command
   line converters (ffmpeg, ImageMagick, Ghostscript, pandoc).

   unvirtualizedResources: (1) converted files are written next to the
   user's originals and Office documents are converted through Microsoft
   Word/Excel/PowerPoint via COM, which run outside the package and must
   see the same %TEMP% and %LOCALAPPDATA% files; (2) only when the user
   explicitly opts in (first-run prompt or Settings switch), the app
   turns off the Windows Alt+Shift / Ctrl+Shift input-language hotkeys
   in HKCU\Keyboard Layout\Toggle, which conflict with its Shift+Alt and
   Shift+Ctrl gestures. The original values are saved and restored from
   the same Settings switch.
   ```

8. **Enviar para a Store.** A certificação costuma levar de 1 a 3 dias
   úteis. Funcionalidades restritas podem pedir uma revisão manual a
   mais.

## Atualizações

1. Suba `__version__` em `mexerica/__init__.py`.
2. `.\build.ps1`
3. Partner Center > Mexerica > **Atualizar** > Pacotes: troque o .msix e,
   se quiser, o texto de "Novidades desta versão".

## Licenças de terceiros

O pacote inclui `THIRD-PARTY-NOTICES.txt` (gerado pelo `pacman -Qi`) e
os textos completos em `runtime\share\licenses`. Alguns componentes são
GPL ou AGPL (ffmpeg com x264/x265, Ghostscript, poppler, pandoc). A
distribuição é permitida desde que o código-fonte esteja disponível: o
aviso aponta para os fontes do MSYS2 (<https://repo.msys2.org/mingw/sources/>)
e do pandoc/exiftool. Para aliviar o pacote, ou para evitar a AGPL do
Ghostscript, tire o pacote da lista `PACKAGES` do `stage.py`: a roda
esconde sozinha as operações que dependem dele.
