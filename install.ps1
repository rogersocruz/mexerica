<#
.SYNOPSIS
  Instala a Mexerica no Windows 10/11 (instalação de usuário, sem administrador).

.DESCRIPTION
  O GTK 4, o PyGObject e os conversores vêm do MSYS2 (ambiente UCRT64): é o
  mesmo GTK do Linux, então a roda e as janelas são as mesmas. Sem o MSYS2,
  o script baixa o pacote base dele e extrai em C:\msys64 (ou em
  %LOCALAPPDATA%\msys64, se C:\ não aceitar), sem administrador.

  O app vai para %LOCALAPPDATA%\Mexerica, o comando `mexerica` entra no
  PATH do usuário e o serviço sobe no login (atalho na pasta Inicializar).
  Os atalhos do Windows que trocam o teclado com Alt+Shift e Ctrl+Shift
  são desligados (windows-hotkeys.ps1): são as teclas das rodas.

  Se o PowerShell recusar o script (política de execução), use o
  install.cmd, que chama este arquivo com -ExecutionPolicy Bypass.

.PARAMETER Converters
  Instala também os conversores: ffmpeg, ImageMagick, libheif, librsvg,
  poppler, qpdf, Ghostscript, zbar, libarchive, typst, PyYAML, fontTools e
  brotli pelo MSYS2; Pandoc e ExifTool pelo winget. Sem isso, a roda mostra
  só o que já existir.

.PARAMETER Calibre
  Instala o calibre (winget, ~200 MB), para e-books MOBI, AZW3 e FB2. O
  EPUB não precisa dele.

.PARAMETER NoContextMenu
  Não acrescenta "Converter com a Mexerica" ao botão direito do Explorer.

.PARAMETER Office
  Instala o LibreOffice (winget, ~350 MB). Em geral não precisa: os
  documentos do Office são convertidos pelo Microsoft Office instalado
  (Word, Excel, PowerPoint) ou, sem ele, pelo pandoc + typst. O LibreOffice
  só acrescenta Pages, Keynote, Numbers e WordPerfect, e o layout fiel de
  planilhas e apresentações numa máquina sem Microsoft Office.

.PARAMETER AppOnly
  Só copia o código para %LOCALAPPDATA%\Mexerica e reinicia o serviço,
  sem mexer no MSYS2 (para atualizar depois de um git pull).

.PARAMETER KeepLayoutHotkeys
  Não mexe nos atalhos de troca de teclado do Windows.

.EXAMPLE
  .\install.ps1 -Converters
#>
param([switch]$Converters, [switch]$Office, [switch]$Calibre, [switch]$AppOnly,
      [switch]$KeepLayoutHotkeys, [switch]$NoContextMenu)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$AppId = 'io.github.rogersocruz.Mexerica'
$Root = Join-Path $env:LOCALAPPDATA 'Mexerica'
$App = Join-Path $Root 'app'
$Bin = Join-Path $Root 'bin'
$Ico = Join-Path $Root 'mexerica.ico'
$Pkg = 'mingw-w64-ucrt-x86_64-'
$MsysBase = 'https://github.com/msys2/msys2-installer/releases/download/nightly-x86_64/msys2-base-x86_64-latest.sfx.exe'

# Elevado, o serviço ficaria acima do Explorer e o Windows bloquearia o
# arraste para a roda; e o "eu" do registro e do LOCALAPPDATA pode ser
# outro usuário (o administrador que digitou a senha).
$identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
$uac = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -ErrorAction SilentlyContinue).EnableLUA -ne 0
if ($uac -and $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Rode sem "Executar como administrador": a instalação é por usuário e não precisa de administrador.'
}

function Find-Winget {
    $cmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    # o winget é um alias em WindowsApps, que nem sempre está no PATH
    $alias = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe'
    if (Test-Path $alias) { return $alias }
    return $null
}

function Find-Msys {
    $candidates = $env:MSYS2_ROOT, 'C:\msys64', (Join-Path $env:LOCALAPPDATA 'msys64'),
                  (Join-Path $env:USERPROFILE 'scoop\apps\msys2\current')
    foreach ($dir in $candidates) {
        if ($dir -and (Test-Path (Join-Path $dir 'usr\bin\bash.exe'))) { return $dir }
    }
    return $null
}

function Install-Msys {
    # O pacote base é só extrair: sem administrador e sem perguntas.
    $parent = 'C:\'
    try {
        $probe = Join-Path $parent "mexerica-$PID"
        New-Item -ItemType Directory -Path $probe | Out-Null
        Remove-Item $probe
    } catch {
        $parent = $env:LOCALAPPDATA
    }
    $sfx = Join-Path $env:TEMP "msys2-base-$PID.sfx.exe"
    Write-Host 'Baixando o MSYS2 (~45 MB)...'
    $downloaded = $false
    try {
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            curl.exe -fL --retry 3 -o $sfx $MsysBase
            $downloaded = $LASTEXITCODE -eq 0
        } else {                        # Windows 10 antes do 1803: sem curl
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -UseBasicParsing -Uri $MsysBase -OutFile $sfx
            $downloaded = $true
        }
    } catch {
        Write-Warning "Download do MSYS2: $($_.Exception.Message)"
    }
    if ($downloaded) {
        Write-Host "Extraindo em $(Join-Path $parent 'msys64')..."
        & $sfx -y "-o$parent" | Out-Null
        Remove-Item $sfx -ErrorAction SilentlyContinue
        $found = Find-Msys
        if ($found) { return $found }
    }
    $winget = Find-Winget
    if ($winget) {
        Write-Host 'Download falhou; tentando o MSYS2 pelo winget...'
        & $winget install --id MSYS2.MSYS2 -e --accept-package-agreements --accept-source-agreements
        $found = Find-Msys
        if ($found) { return $found }
    }
    throw 'Não consegui instalar o MSYS2. Instale de https://www.msys2.org (em C:\msys64) e rode de novo.'
}

function Invoke-Pacman([string[]]$Arguments) {
    # MSYSTEM só para o bash: herdado pelo serviço, mudaria o Python do MSYS2
    $env:MSYSTEM = 'UCRT64'
    $env:CHERE_INVOKING = '1'
    try {
        & (Join-Path $Msys 'usr\bin\bash.exe') -lc "pacman $($Arguments -join ' ')" | Out-Host
        return ($LASTEXITCODE -eq 0)
    } finally {
        Remove-Item Env:MSYSTEM, Env:CHERE_INVOKING -ErrorAction SilentlyContinue
    }
}

function Stop-Mexerica {
    # Pede para sair pela janela da bandeja (o ícone some direito); quem não
    # sair em 3 s é encerrado.
    if (-not ('Mexerica.Tray' -as [type])) {
        Add-Type -Namespace Mexerica -Name Tray -MemberDefinition @'
[DllImport("user32.dll", CharSet = CharSet.Unicode)]
public static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string title);
[DllImport("user32.dll")]
public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr w, IntPtr l);
'@
    }
    $hwnd = [IntPtr]::Zero
    while (($hwnd = [Mexerica.Tray]::FindWindowEx([IntPtr]::Zero, $hwnd, 'MexericaTray', $null)) -ne [IntPtr]::Zero) {
        [Mexerica.Tray]::PostMessage($hwnd, 0x10, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
    }
    $deadline = (Get-Date).AddSeconds(3)
    do {
        $left = @(Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'" |
            Where-Object { $_.CommandLine -match '-m mexerica( daemon)?\s*$' })
        if (-not $left) { return }
        Start-Sleep -Milliseconds 300
    } while ((Get-Date) -lt $deadline)
    $left | ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
}

function Send-SettingChange {
    # avisa o Explorer que o PATH mudou (vale para os terminais abertos depois)
    if (-not ('Mexerica.Win32' -as [type])) {
        Add-Type -Namespace Mexerica -Name Win32 -MemberDefinition @'
[DllImport("user32.dll", CharSet = CharSet.Unicode)]
public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, UIntPtr wParam,
    string lParam, uint flags, uint timeout, out UIntPtr result);
'@
    }
    $result = [UIntPtr]::Zero
    [Mexerica.Win32]::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]::Zero,
        'Environment', 2, 5000, [ref]$result) | Out-Null
}

function ConvertTo-CmdPath([string]$Path) {
    # no .cmd, caminhos do perfil viram %LOCALAPPDATA%/%USERPROFILE%: o
    # cmd.exe lê o arquivo na página de código do console e erraria acentos
    foreach ($var in 'LOCALAPPDATA', 'USERPROFILE') {
        $value = [Environment]::GetEnvironmentVariable($var)
        if ($value -and $Path.StartsWith($value, [StringComparison]::OrdinalIgnoreCase)) {
            return "%$var%" + $Path.Substring($value.Length)
        }
    }
    return $Path
}

# --- MSYS2 ------------------------------------------------------------------
$Msys = Find-Msys
if (-not $Msys) {
    if ($AppOnly) { throw 'MSYS2 não encontrado: rode o install.ps1 sem -AppOnly primeiro.' }
    $Msys = Install-Msys
}
$Ucrt = Join-Path $Msys 'ucrt64\bin'
$Py = Join-Path $Ucrt 'python.exe'
$PyW = Join-Path $Ucrt 'pythonw.exe'
Write-Host "MSYS2: $Msys"

# (com -AppOnly: só copia o app e reinicia o serviço)
if (-not $AppOnly) {
    Write-Host 'Atualizando o MSYS2...'
    # a primeira atualização pode trocar só o núcleo e encerrar o pacman
    Invoke-Pacman @('-Syu', '--noconfirm') | Out-Null
    Invoke-Pacman @('-Syu', '--noconfirm') | Out-Null

    $required = 'python', 'gtk4', 'python-gobject', 'python-cairo', 'adwaita-icon-theme' |
        ForEach-Object { $Pkg + $_ }
    if (-not (Invoke-Pacman (@('-S', '--needed', '--noconfirm') + $required))) {
        throw 'O pacman não instalou o GTK 4 e o PyGObject (sem internet?).'
    }

    if ($Converters) {
        # um por vez: se algum faltar no repositório, os outros entram
        foreach ($name in 'ffmpeg', 'imagemagick', 'libheif', 'librsvg', 'poppler',
                          'qpdf', 'ghostscript', 'zbar', 'libarchive', 'typst',
                          'python-yaml', 'python-fonttools', 'python-brotli') {
            if (-not (Invoke-Pacman @('-S', '--needed', '--noconfirm', ($Pkg + $name)))) {
                Write-Warning "pacman: $name não foi instalado"
            }
        }
    }
    $wingetIds = @()
    if ($Converters) { $wingetIds += 'JohnMacFarlane.Pandoc', 'OliverBetz.ExifTool' }
    if ($Office) { $wingetIds += 'TheDocumentFoundation.LibreOffice' }
    if ($Calibre) { $wingetIds += 'calibre.calibre' }
    if ($wingetIds) {
        $winget = Find-Winget
        if ($winget) {
            foreach ($id in $wingetIds) {
                & $winget install --id $id -e --accept-package-agreements --accept-source-agreements
            }
        } else {
            Write-Warning "winget não encontrado: instale à mão $($wingetIds -join ', ')."
        }
    }
}

& $Py -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk"
if ($LASTEXITCODE -ne 0) {
    throw 'O Python do MSYS2 não carregou o GTK 4 (PyGObject). Rode sem -AppOnly.'
}

# --- arquivos -----------------------------------------------------------------
Stop-Mexerica
New-Item -ItemType Directory -Force -Path $App, $Bin | Out-Null
$dest = Join-Path $App 'mexerica'
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse 'mexerica' $dest
Get-ChildItem $dest -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
Copy-Item "data\icons\$AppId.ico" $Ico -Force
Copy-Item 'bin\mexerica-open.pyw' $App -Force

$launcher = Get-Content -Raw 'bin\mexerica.cmd.in'
$launcher = $launcher.Replace('@PYTHON@', (ConvertTo-CmdPath $Py)).Replace('@PKGDATADIR@', '%~dp0..\app')
[IO.File]::WriteAllText((Join-Path $Bin 'mexerica.cmd'), $launcher,
    (New-Object Text.UTF8Encoding $false))

# comando `mexerica` no PATH do usuário (sem expandir as variáveis que já existem)
$userPath = (Get-Item 'HKCU:\Environment').GetValue('Path', '', 'DoNotExpandEnvironmentNames')
if (($userPath -split ';') -notcontains $Bin) {
    $newPath = if ($userPath) { "$userPath;$Bin" } else { $Bin }
    Set-ItemProperty 'HKCU:\Environment' -Name 'Path' -Value $newPath -Type ExpandString
    Send-SettingChange
}

# menu Iniciar (abre a janela de status) e Inicializar (sobe o serviço no login)
$shell = New-Object -ComObject WScript.Shell
function New-Shortcut([string]$Path, [string]$Arguments, [string]$Description) {
    $lnk = $shell.CreateShortcut($Path)
    $lnk.TargetPath = $PyW
    $lnk.Arguments = $Arguments
    $lnk.WorkingDirectory = $App        # o `python -m` acha o pacote aqui
    $lnk.Description = $Description
    $lnk.IconLocation = $Ico
    $lnk.Save()
}
New-Shortcut (Join-Path ([Environment]::GetFolderPath('Programs')) 'Mexerica.lnk') `
    '-X utf8 -m mexerica' 'Converta arquivos segurando Shift enquanto arrasta'
# desligado em Configurações > Comportamento: o atalho fica guardado fora da
# pasta Inicializar e continua desligado
$startupLink = Join-Path ([Environment]::GetFolderPath('Startup')) 'Mexerica (serviço).lnk'
$parkedLink = Join-Path $Root 'autostart-off.lnk'
if (Test-Path $parkedLink) { $startupLink = $parkedLink }
New-Shortcut $startupLink '-X utf8 -m mexerica daemon' 'Mantém a roda de conversão pronta para abrir sem atraso'

# botão direito do Explorer, em arquivos e pastas: abre a janela Início com
# eles (no Windows 11, em "Mostrar mais opções"). Pelo .NET: o "*" do
# caminho seria um curinga para os cmdlets do registro.
function Set-ContextMenu([string]$Class) {
    $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey("Software\Classes\$Class\shell\Mexerica")
    $key.SetValue('MUIVerb', 'Converter com a Mexerica')
    $key.SetValue('Icon', $Ico)
    $command = $key.CreateSubKey('command')
    $command.SetValue('', "`"$PyW`" -X utf8 `"$(Join-Path $App 'mexerica-open.pyw')`" `"%1`"")
    $command.Close()
    $key.Close()
}
if ($NoContextMenu) {
    foreach ($class in '*', 'Directory') {
        [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree("Software\Classes\$class\shell\Mexerica", $false)
    }
} else {
    Set-ContextMenu '*'
    Set-ContextMenu 'Directory'
}

# Alt+Shift e Ctrl+Shift trocam o teclado: são as teclas das rodas
if (-not $KeepLayoutHotkeys) {
    & (Join-Path $PSScriptRoot 'windows-hotkeys.ps1')
}

# --- serviço --------------------------------------------------------------------
Start-Process -FilePath $PyW -ArgumentList '-X', 'utf8', '-m', 'mexerica', 'daemon' -WorkingDirectory $App

Write-Host ''
$env:PYTHONPATH = $App
& $Py -X utf8 -m mexerica doctor
Write-Host @"

Instalado e rodando (ícone da Mexerica perto do relógio). Arraste um arquivo
no Explorer e segure Shift (Shift+Alt: ferramentas, Shift+Ctrl: ações), ou
clique com o botão direito > "Converter com a Mexerica" (no Windows 11, em
"Mostrar mais opções"). Janela Início e Configurações: clique no ícone da
bandeja ou abra "Mexerica" no menu Iniciar.

O comando mexerica vale nos terminais abertos a partir de agora.
Log: $Root\cache\mexerica.log
"@
