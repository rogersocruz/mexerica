<#
.SYNOPSIS
  Desliga (ou devolve, com -Restore) os atalhos do Windows que trocam o
  idioma com Alt+Shift e o layout do teclado com Ctrl+Shift.

.DESCRIPTION
  Shift+Alt abre a roda de ferramentas e Shift+Ctrl a de ações. Com mais
  de um teclado ou idioma instalado, o Windows usa as mesmas teclas para
  trocar de teclado: cada roda aberta trocaria o teclado junto. Este script
  desliga só esses dois atalhos (um atalho com a tecla ` fica como está).
  Win+Espaço continua trocando o teclado.

  Os valores originais ficam em %LOCALAPPDATA%\Mexerica\layout-hotkeys.json;
  -Restore os devolve (o uninstall.ps1 faz isso). Vale na hora, sem sair
  da sessão.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\windows-hotkeys.ps1 -Restore
#>
param([switch]$Restore)

$ErrorActionPreference = 'Stop'

$Key = 'HKCU:\Keyboard Layout\Toggle'
$Backup = Join-Path $env:LOCALAPPDATA 'Mexerica\layout-hotkeys.json'
# valor ausente = padrão do Windows: idioma com Alt+Shift (1), layout com Ctrl+Shift (2)
$Names = 'Hotkey', 'Language Hotkey', 'Layout Hotkey'
$Off = '3'

function Update-LangToggle {
    # SPI_SETLANGTOGGLE: o Windows relê os atalhos do registro na hora
    if (-not ('MexericaKeyboard.Native' -as [type])) {
        Add-Type -Namespace MexericaKeyboard -Name Native -MemberDefinition @'
[DllImport("user32.dll", SetLastError = true)]
public static extern bool SystemParametersInfo(uint action, uint uiParam, IntPtr pvParam, uint winIni);
'@
    }
    [MexericaKeyboard.Native]::SystemParametersInfo(0x5B, 0, [IntPtr]::Zero, 2) | Out-Null
}

if (-not (Test-Path $Key)) { New-Item -Path $Key | Out-Null }
$current = Get-ItemProperty -Path $Key

if ($Restore) {
    if (-not (Test-Path $Backup)) {
        Write-Host 'Atalhos de troca de teclado: nada para restaurar.'
        return
    }
    $saved = Get-Content -Raw -Path $Backup | ConvertFrom-Json
    foreach ($name in $Names) {
        $value = $saved.$name
        if ($null -eq $value) {
            Remove-ItemProperty -Path $Key -Name $name -ErrorAction SilentlyContinue
        } else {
            Set-ItemProperty -Path $Key -Name $name -Value $value -Type String
        }
    }
    Remove-Item -Path $Backup
    Update-LangToggle
    Write-Host 'Atalhos de troca de teclado (Alt+Shift e Ctrl+Shift) restaurados.'
    return
}

# só o que conflita com a roda: ausente (padrão), 1 = Alt+Shift, 2 = Ctrl+Shift
$conflicting = @($Names | Where-Object { @($null, '1', '2') -contains $current.$_ })
if (-not $conflicting) {
    Write-Host 'Atalhos de troca de teclado: já não usam Alt+Shift nem Ctrl+Shift.'
    return
}

if (-not (Test-Path $Backup)) {
    # guarda só o original: rodar de novo não perde o que havia antes
    $saved = [ordered]@{}
    foreach ($name in $Names) { $saved[$name] = $current.$name }
    New-Item -ItemType Directory -Force -Path (Split-Path $Backup) | Out-Null
    $saved | ConvertTo-Json | Set-Content -Path $Backup -Encoding UTF8
}
foreach ($name in $conflicting) {
    Set-ItemProperty -Path $Key -Name $name -Value $Off -Type String
}
Update-LangToggle

Write-Warning @'
Desliguei os atalhos do Windows que trocam o teclado com Alt+Shift e
Ctrl+Shift: são as mesmas teclas das rodas de ferramentas (Shift+Alt) e de
ações (Shift+Ctrl), e cada roda aberta trocaria o teclado junto.
Para trocar de teclado agora: Win+Espaço.
Para voltar como era: .\windows-hotkeys.ps1 -Restore
'@
