<#
.SYNOPSIS
  Gera o pacote MSIX da Mexerica para a Microsoft Store.

.DESCRIPTION
  1. Garante no MSYS2 (UCRT64) o GTK 4, o PyGObject e os conversores (o
     mesmo do install.ps1 -Converters).
  2. stage.py monta build\stage: o runtime do MSYS2 que a Mexerica usa, o
     app, pandoc e exiftool, os logos e o AppxManifest.xml.
  3. Compila o launcher.cs nos três .exe do pacote (csc.exe do .NET
     Framework, que vem no Windows).
  4. makepri (resources.pri dos logos) e makeappx: dist\Mexerica_<versão>_x64.msix.
  5. Com -Sign, assina com um certificado de teste, para instalar nesta
     máquina antes de enviar. Para a Store não precisa: ela assina.

  Precisa do Windows SDK (makeappx, makepri, signtool):
  winget install Microsoft.WindowsSDK.10.0.26100

.PARAMETER Version
  Versão do pacote (a.b.c.0; a Store exige o último número 0 e que cada
  envio seja maior que o anterior). Padrão: __version__ do mexerica + ".0".

.PARAMETER Sign
  Assina com um certificado autoassinado (CN do store.json). Para instalar
  o .msix de teste, o certificado precisa estar em "Pessoas Confiáveis" da
  máquina (veja o README desta pasta).

.PARAMETER SkipUpdate
  Não roda o pacman (usa o MSYS2 como está).

.EXAMPLE
  .\build.ps1 -Sign
#>
param([string]$Version, [switch]$Sign, [switch]$SkipUpdate, [string]$Msys)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Repo = (Resolve-Path '..\..').Path
$Build = Join-Path $PSScriptRoot 'build'
$Stage = Join-Path $Build 'stage'
$Dist = Join-Path $PSScriptRoot 'dist'
$Pkg = 'mingw-w64-ucrt-x86_64-'

# --- ferramentas ------------------------------------------------------------
if (-not $Msys) {
    $Msys = $env:MSYS2_ROOT, 'C:\msys64', (Join-Path $env:LOCALAPPDATA 'msys64') |
        Where-Object { $_ -and (Test-Path (Join-Path $_ 'usr\bin\bash.exe')) } |
        Select-Object -First 1
}
if (-not $Msys) { throw 'MSYS2 não encontrado: rode o install.ps1 uma vez ou passe -Msys.' }
$Py = Join-Path $Msys 'ucrt64\bin\python.exe'

function Find-SdkTool([string]$Name) {
    $kits = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    $found = Get-ChildItem $kits -Directory -Filter '10.*' -ErrorAction SilentlyContinue |
        Sort-Object { [version]$_.Name } -Descending |
        ForEach-Object { Join-Path $_.FullName "x64\$Name" } |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $found) { throw "$Name não encontrado: instale o Windows SDK (winget install Microsoft.WindowsSDK.10.0.26100)." }
    return $found
}
$MakeAppx = Find-SdkTool 'makeappx.exe'
$MakePri = Find-SdkTool 'makepri.exe'
$Csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $Csc)) { throw "csc.exe não encontrado em $Csc (.NET Framework 4)." }

if (-not $Version) {
    $init = Get-Content -Raw (Join-Path $Repo 'mexerica\__init__.py')
    if ($init -notmatch '__version__ = "(\d+)\.(\d+)\.(\d+)"') { throw 'sem __version__ em mexerica\__init__.py' }
    $Version = "$($Matches[1]).$($Matches[2]).$($Matches[3]).0"
}
if ($Version -notmatch '^\d+\.\d+\.\d+\.0$') { throw "Versão inválida para a Store: $Version (use a.b.c.0)" }

$identity = Get-Content -Raw 'store.json' | ConvertFrom-Json
if ($identity.identityName -eq 'io.github.rogersocruz.Mexerica') {
    Write-Warning 'store.json ainda tem a identidade de teste. Antes de enviar, troque pelos valores de Partner Center > Identidade do produto.'
}

# --- 1. MSYS2 ------------------------------------------------------------------
if (-not $SkipUpdate) {
    $names = 'python', 'gtk4', 'python-gobject', 'python-cairo', 'adwaita-icon-theme',
             'ffmpeg', 'imagemagick', 'libheif', 'librsvg', 'poppler', 'qpdf',
             'ghostscript', 'zbar', 'libarchive', 'typst', 'python-yaml',
             'python-fonttools', 'python-brotli' | ForEach-Object { $Pkg + $_ }
    $env:MSYSTEM = 'UCRT64'
    try {
        & (Join-Path $Msys 'usr\bin\bash.exe') -lc "pacman -S --needed --noconfirm $($names -join ' ')"
        if ($LASTEXITCODE -ne 0) { throw 'pacman falhou' }
    } finally { Remove-Item Env:MSYSTEM -ErrorAction SilentlyContinue }
}

# --- 2. pasta do pacote --------------------------------------------------------
& $Py -X utf8 (Join-Path $PSScriptRoot 'stage.py') --msys $Msys --out $Stage --version $Version
if ($LASTEXITCODE -ne 0) { throw 'stage.py falhou' }

# --- 3. launchers --------------------------------------------------------------
$bin = Join-Path $Stage 'runtime\bin'
$ico = Join-Path $Repo 'data\icons\io.github.rogersocruz.Mexerica.ico'
$launchers = @(
    @{ Name = 'Mexerica.exe'; Target = 'winexe'; Define = $null },
    @{ Name = 'MexericaService.exe'; Target = 'winexe'; Define = 'SERVICE' },
    @{ Name = 'mexerica-cli.exe'; Target = 'exe'; Define = 'CONSOLE' }
)
foreach ($l in $launchers) {
    $cscArgs = @('/nologo', '/optimize+', "/target:$($l.Target)", "/win32icon:$ico",
                 "/out:$(Join-Path $bin $l.Name)")
    if ($l.Define) { $cscArgs += "/define:$($l.Define)" }
    & $Csc @cscArgs (Join-Path $PSScriptRoot 'launcher.cs')
    if ($LASTEXITCODE -ne 0) { throw "csc falhou ($($l.Name))" }
}

# --- 4. resources.pri e .msix --------------------------------------------------
# o makepri indexa a pasta inteira: só os logos e o manifesto, à parte
$pri = Join-Path $Build 'pri'
if (Test-Path $pri) { Remove-Item -Recurse -Force $pri }
New-Item -ItemType Directory -Path $pri | Out-Null
Copy-Item -Recurse (Join-Path $Stage 'Assets') $pri
Copy-Item (Join-Path $Stage 'AppxManifest.xml') $pri
function Invoke-Quiet([string]$Tool, [string[]]$Arguments) {
    # a saída só aparece se der erro (o makeappx lista arquivo por arquivo)
    $out = & $Tool @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        # (só as linhas de erro: "dialog-error.png" também tem "error")
        $out | Where-Object { "$_" -match '^\S+ : error' } | ForEach-Object { Write-Host "$_" }
        throw "$(Split-Path -Leaf $Tool) falhou"
    }
}
$priConfig = Join-Path $Build 'priconfig.xml'
Invoke-Quiet $MakePri @('createconfig', '/cf', $priConfig, '/dq', 'pt-BR', '/pv', '10.0.0', '/o')
Invoke-Quiet $MakePri @('new', '/pr', $pri, '/cf', $priConfig, '/mn', (Join-Path $pri 'AppxManifest.xml'),
                        '/of', (Join-Path $Stage 'resources.pri'), '/o')

New-Item -ItemType Directory -Force -Path $Dist | Out-Null
$msix = Join-Path $Dist "Mexerica_$($Version)_x64.msix"
Invoke-Quiet $MakeAppx @('pack', '/d', $Stage, '/p', $msix, '/o', '/h', 'SHA256')

# --- 5. assinatura de teste ------------------------------------------------------
if ($Sign) {
    $SignTool = Find-SdkTool 'signtool.exe'
    $cert = Get-ChildItem Cert:\CurrentUser\My |
        Where-Object { $_.Subject -eq $identity.publisher -and $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date) } |
        Select-Object -First 1
    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type Custom -Subject $identity.publisher `
            -KeyUsage DigitalSignature -FriendlyName 'Mexerica (teste do MSIX)' `
            -CertStoreLocation Cert:\CurrentUser\My `
            -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}')
    }
    $cer = Join-Path $Dist 'Mexerica-teste.cer'
    Export-Certificate -Cert $cert -FilePath $cer | Out-Null
    & $SignTool sign /fd SHA256 /sha1 $cert.Thumbprint $msix
    if ($LASTEXITCODE -ne 0) { throw 'signtool falhou' }
    Write-Host "Certificado de teste: $cer"
}

$size = [math]::Round((Get-Item $msix).Length / 1MB)
Write-Host ''
Write-Host "Pacote: $msix ($size MB)"
if (-not $Sign) { Write-Host 'Envie este arquivo em Partner Center > Pacotes (a Store assina).' }
