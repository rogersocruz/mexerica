<#
.SYNOPSIS
  Remove a Mexerica do Windows (o que o install.ps1 instalou). O MSYS2 fica.
#>
$ErrorActionPreference = 'Stop'

$Root = Join-Path $env:LOCALAPPDATA 'Mexerica'
$Bin = Join-Path $Root 'bin'

Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'" |
    Where-Object { $_.CommandLine -match '-m mexerica( daemon)?\s*$' } |
    ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }

Remove-Item -Force -ErrorAction SilentlyContinue `
    (Join-Path ([Environment]::GetFolderPath('Programs')) 'Mexerica.lnk'),
    (Join-Path ([Environment]::GetFolderPath('Startup')) 'Mexerica (serviço).lnk')
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
    (Join-Path $Root 'app'), $Bin, (Join-Path $Root 'mexerica.ico')

$userPath = (Get-Item 'HKCU:\Environment').GetValue('Path', '', 'DoNotExpandEnvironmentNames')
$parts = $userPath -split ';' | Where-Object { $_ -and $_ -ne $Bin }
if ($parts.Count -ne ($userPath -split ';' | Where-Object { $_ }).Count) {
    Set-ItemProperty 'HKCU:\Environment' -Name 'Path' -Value ($parts -join ';') -Type ExpandString
}

Write-Host "Removido. Log e cache em $Root\cache (apague se quiser). O MSYS2 continua instalado."
