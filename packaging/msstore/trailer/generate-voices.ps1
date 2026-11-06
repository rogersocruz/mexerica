$ErrorActionPreference = 'Stop'
$trailerCues = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'audio-script.json') -Encoding UTF8 -Raw | ConvertFrom-Json
$trailerWork = Join-Path $PSScriptRoot 'work'
New-Item -ItemType Directory -Path $trailerWork -Force | Out-Null
foreach ($trailerLanguage in @('pt-BR', 'en-US')) {
    $trailerVoice = New-Object -ComObject SAPI.SpVoice
    $trailerName = if ($trailerLanguage -eq 'pt-BR') { 'Maria' } else { 'Zira' }
    $trailerSelected = @($trailerVoice.GetVoices() | Where-Object { $_.GetDescription() -like "*$trailerName*" })
    if ($trailerSelected.Count -eq 0) { throw "Missing voice: $trailerName" }
    $trailerVoice.Voice = $trailerSelected[0]
    $trailerVoice.Rate = 1
    for ($trailerIndex = 0; $trailerIndex -lt $trailerCues.Count; $trailerIndex++) {
        $trailerStream = New-Object -ComObject SAPI.SpFileStream
        $trailerStream.Format.Type = 22
        $trailerStream.Open((Join-Path $trailerWork "$trailerLanguage-$trailerIndex.wav"), 3, $false)
        $trailerVoice.AudioOutputStream = $trailerStream
        [void]$trailerVoice.Speak([string]$trailerCues[$trailerIndex].$trailerLanguage)
        $trailerStream.Close()
    }
}
