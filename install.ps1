<#
.SYNOPSIS
  Instala a Mexerica no Windows 11 (instalação de usuário, sem administrador).

.DESCRIPTION
  O GTK 4, o PyGObject e os conversores vêm do MSYS2 (ambiente UCRT64): é o
  mesmo GTK do Linux, então a roda e as janelas são as mesmas. O pacote vai
  para %LOCALAPPDATA%\Mexerica, o comando `mexerica` entra no PATH do
  usuário e o serviço sobe no login (atalho na pasta Inicializar).

.PARAMETER Converters
  Instala também os conversores: ffmpeg, ImageMagick, poppler, qpdf,
  Ghostscript, librsvg, zbar e libarchive pelo MSYS2; Pandoc, ExifTool e
  LibreOffice pelo winget. Sem isso, a roda mostra só o que já existir.

.PARAMETER AppOnly
  Só copia o código para %LOCALAPPDATA%\Mexerica e reinicia o serviço,
  sem mexer no MSYS2 (para atualizar depois de um git pull).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Converters
#>
param([switch]$Converters, [switch]$AppOnly)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$AppId = 'io.github.rogersocruz.Mexerica'
$Msys = if ($env:MSYS2_ROOT) { $env:MSYS2_ROOT } else { 'C:\msys64' }
$Ucrt = Join-Path $Msys 'ucrt64\bin'
$Py = Join-Path $Ucrt 'python.exe'
$PyW = Join-Path $Ucrt 'pythonw.exe'
$Root = Join-Path $env:LOCALAPPDATA 'Mexerica'
$App = Join-Path $Root 'app'
$Bin = Join-Path $Root 'bin'
$Ico = Join-Path $Root 'mexerica.ico'
$Pkg = 'mingw-w64-ucrt-x86_64-'

function Invoke-Pacman([string[]]$Arguments) {
    $env:MSYSTEM = 'UCRT64'
    $env:CHERE_INVOKING = '1'
    & (Join-Path $Msys 'usr\bin\bash.exe') -lc "pacman $($Arguments -join ' ')" | Out-Host
    return ($LASTEXITCODE -eq 0)
}

function Find-Winget {
    $cmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    # o winget é um alias em WindowsApps, que nem sempre está no PATH
    $alias = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe'
    if (Test-Path $alias) { return $alias }
    return $null
}
$Winget = Find-Winget

function Stop-Mexerica {
    Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'" |
        Where-Object { $_.CommandLine -match '-m mexerica( daemon)?\s*$' } |
        ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
}

function Send-SettingChange {
    # avisa o Explorer que o PATH mudou (vale para os terminais abertos depois)
    Add-Type -Namespace Mexerica -Name Win32 -MemberDefinition @'
[DllImport("user32.dll", CharSet = CharSet.Unicode)]
public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, UIntPtr wParam,
    string lParam, uint flags, uint timeout, out UIntPtr result);
'@
    $result = [UIntPtr]::Zero
    [Mexerica.Win32]::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]::Zero,
        'Environment', 2, 5000, [ref]$result) | Out-Null
}

# --- MSYS2 ------------------------------------------------------------------
# (com -AppOnly: só copia o app e reinicia o serviço)
if (-not $AppOnly) {
    if (-not (Test-Path (Join-Path $Msys 'usr\bin\bash.exe'))) {
        if (-not $Winget) {
            throw "MSYS2 não encontrado em $Msys e winget indisponível. Instale de https://www.msys2.org e rode de novo."
        }
        Write-Host 'Instalando o MSYS2 (winget)...'
        & $Winget install --id MSYS2.MSYS2 -e --accept-package-agreements --accept-source-agreements
        if (-not (Test-Path (Join-Path $Msys 'usr\bin\bash.exe'))) {
            throw "MSYS2 não ficou em $Msys. Defina MSYS2_ROOT se instalou em outro lugar."
        }
    }

    Write-Host 'Atualizando o MSYS2...'
    # a primeira atualização pode trocar só o núcleo e encerrar o pacman
    Invoke-Pacman @('-Syu', '--noconfirm') | Out-Null
    Invoke-Pacman @('-Syu', '--noconfirm') | Out-Null

    $required = 'python', 'gtk4', 'python-gobject', 'python-cairo', 'adwaita-icon-theme' |
        ForEach-Object { $Pkg + $_ }
    if (-not (Invoke-Pacman (@('-S', '--needed', '--noconfirm') + $required))) {
        throw 'O pacman não instalou o GTK 4 e o PyGObject.'
    }

    if ($Converters) {
        # um por vez: se algum faltar no repositório, os outros entram
        foreach ($name in 'ffmpeg', 'imagemagick', 'libheif', 'librsvg', 'poppler',
                          'qpdf', 'ghostscript', 'zbar', 'libarchive') {
            if (-not (Invoke-Pacman @('-S', '--needed', '--noconfirm', ($Pkg + $name)))) {
                Write-Warning "pacman: $name não foi instalado"
            }
        }
        if ($Winget) {
            foreach ($id in 'JohnMacFarlane.Pandoc', 'OliverBetz.ExifTool',
                            'TheDocumentFoundation.LibreOffice') {
                & $Winget install --id $id -e --accept-package-agreements --accept-source-agreements
            }
        } else {
            Write-Warning 'winget não encontrado: instale Pandoc, ExifTool e LibreOffice à mão.'
        }
    }
}

& $Py -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk"
if ($LASTEXITCODE -ne 0) {
    throw 'O Python do MSYS2 não carregou o GTK 4 (PyGObject).'
}

# --- arquivos -----------------------------------------------------------------
Stop-Mexerica
New-Item -ItemType Directory -Force -Path $App, $Bin | Out-Null
$dest = Join-Path $App 'mexerica'
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse 'mexerica' $dest
Get-ChildItem $dest -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force

$launcher = (Get-Content -Raw 'bin\mexerica.cmd.in').Replace('@PYTHON@', $Py).Replace('@PKGDATADIR@', $App)
[IO.File]::WriteAllText((Join-Path $Bin 'mexerica.cmd'), $launcher,
    (New-Object Text.UTF8Encoding $false))

$magick = Join-Path $Ucrt 'magick.exe'
if (-not (Test-Path $Ico) -and (Test-Path $magick)) {
    & $magick -background none "data\icons\$AppId.svg" -define 'icon:auto-resize=256,64,48,32,16' $Ico
}

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
    if (Test-Path $Ico) { $lnk.IconLocation = $Ico }
    $lnk.Save()
}
New-Shortcut (Join-Path ([Environment]::GetFolderPath('Programs')) 'Mexerica.lnk') `
    '-X utf8 -m mexerica' 'Converta arquivos segurando Shift enquanto arrasta'
New-Shortcut (Join-Path ([Environment]::GetFolderPath('Startup')) 'Mexerica (serviço).lnk') `
    '-X utf8 -m mexerica daemon' 'Mantém a roda de conversão pronta para abrir sem atraso'

# --- serviço --------------------------------------------------------------------
Start-Process -FilePath $PyW -ArgumentList '-X', 'utf8', '-m', 'mexerica', 'daemon' -WorkingDirectory $App

Write-Host ''
$env:PYTHONPATH = $App
& $Py -X utf8 -m mexerica doctor
Write-Host @"

Instalado e rodando. Arraste um arquivo no Explorer e segure Shift
(Shift+Alt: ferramentas, Shift+Ctrl: ações). O serviço sobe sozinho no login.

O comando `mexerica` vale nos terminais abertos a partir de agora.
Log: $Root\cache\mexerica.log
"@
