<#
.SYNOPSIS
  Remove a Mexerica do Windows (o que o install.ps1 instalou) e devolve os
  atalhos de troca de teclado. O MSYS2 e os conversores ficam.
#>
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$Root = Join-Path $env:LOCALAPPDATA 'Mexerica'
$Bin = Join-Path $Root 'bin'

# pede para sair pela janela da bandeja (o ícone some direito); quem não
# sair em 3 s é encerrado
Add-Type -Namespace Mexerica -Name Tray -MemberDefinition @'
[DllImport("user32.dll", CharSet = CharSet.Unicode)]
public static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string title);
[DllImport("user32.dll")]
public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr w, IntPtr l);
'@
$hwnd = [IntPtr]::Zero
while (($hwnd = [Mexerica.Tray]::FindWindowEx([IntPtr]::Zero, $hwnd, 'MexericaTray', $null)) -ne [IntPtr]::Zero) {
    [Mexerica.Tray]::PostMessage($hwnd, 0x10, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
}
$deadline = (Get-Date).AddSeconds(3)
do {
    $left = @(Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe' OR Name = 'mexerica-app.exe'" |
        Where-Object { $_.CommandLine -match '-m mexerica( daemon)?\s*$' })
    if ($left) { Start-Sleep -Milliseconds 300 }
} while ($left -and (Get-Date) -lt $deadline)
$left | ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }

# o mexerica-app.exe (ao lado do Python do MSYS2): o atalho diz onde está
$shellApp = New-Object -ComObject WScript.Shell
foreach ($lnkPath in (Join-Path ([Environment]::GetFolderPath('Programs')) 'Mexerica.lnk'),
                     (Join-Path ([Environment]::GetFolderPath('Startup')) 'Mexerica (serviço).lnk'),
                     (Join-Path $Root 'autostart-off.lnk')) {
    if (Test-Path $lnkPath) {
        $target = $shellApp.CreateShortcut($lnkPath).TargetPath
        if ($target -and (Split-Path -Leaf $target) -eq 'mexerica-app.exe') {
            Remove-Item -Force -ErrorAction SilentlyContinue $target
        }
    }
}

Remove-Item -Force -ErrorAction SilentlyContinue `
    (Join-Path ([Environment]::GetFolderPath('Programs')) 'Mexerica.lnk'),
    (Join-Path ([Environment]::GetFolderPath('Startup')) 'Mexerica (serviço).lnk'),
    (Join-Path $Root 'autostart-off.lnk')
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
    (Join-Path $Root 'app'), $Bin, (Join-Path $Root 'mexerica.ico')
# "Converter com a Mexerica" do botão direito (pelo .NET: o "*" do caminho
# seria um curinga para os cmdlets do registro)
foreach ($class in '*', 'Directory') {
    [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree("Software\Classes\$class\shell\Mexerica", $false)
}
# "Ações da Mexerica" (item de menu das versões de teste da 0.2.0)
foreach ($class in '*', 'Directory', 'Directory\Background') {
    [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree("Software\Classes\$class\shell\MexericaWheel", $false)
}

$userPath = (Get-Item 'HKCU:\Environment').GetValue('Path', '', 'DoNotExpandEnvironmentNames')
$parts = $userPath -split ';' | Where-Object { $_ -and $_ -ne $Bin }
if ($parts.Count -ne ($userPath -split ';' | Where-Object { $_ }).Count) {
    Set-ItemProperty 'HKCU:\Environment' -Name 'Path' -Value ($parts -join ';') -Type ExpandString
}

& (Join-Path $PSScriptRoot 'windows-hotkeys.ps1') -Restore

Write-Host "Removido. Log e cache em $Root\cache e configurações em"
Write-Host "$env:APPDATA\Mexerica (apague se quiser)."
Write-Host 'O MSYS2 e os conversores continuam instalados.'
