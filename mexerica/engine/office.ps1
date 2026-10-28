<#
  Converte um documento pelo Microsoft Office (automação COM), sem janela.
  Quem chama é o motor (mexerica/engine/office.py):

    office.ps1 <word|excel|powerpoint> <entrada> <saída> <formato>

  A automação pode pegar o Office que a pessoa está usando. Por isso o
  script nunca mexe na visibilidade (uma instância nova já nasce
  invisível), devolve os avisos como estavam e só encerra o programa se
  não houver nenhum outro documento aberto nele.
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('word', 'excel', 'powerpoint')][string]$App,
    [Parameter(Mandatory = $true)][string]$InputPath,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [Parameter(Mandatory = $true)][string]$Format
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
trap { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }

# Senha falsa: um documento protegido dá erro em vez de abrir um pedido de
# senha numa janela invisível (o processo ficaria esperando para sempre).
$NoPassword = 'mexerica-sem-senha'
$ext = [IO.Path]::GetExtension($InputPath).TrimStart('.').ToLower()

function Invoke-Com($Object, [string]$Method, $Arguments) {
    # Por nome, pelo IDispatch: o PowerShell não passa valores aos parâmetros
    # "ref" do Word ("não é possível converter True em Object"), e por nome
    # os opcionais do meio ficam de fora. Os valores vão sem o embrulho
    # PSObject (o que uma função devolve vem embrulhado, e o Excel recusa:
    # DISP_E_TYPEMISMATCH).
    $values = New-Object 'System.Collections.Generic.List[object]'
    foreach ($value in $Arguments.Values) { $values.Add($value.PSObject.BaseObject) }
    [System.__ComObject].InvokeMember($Method, [Reflection.BindingFlags]::InvokeMethod,
        $null, $Object, $values.ToArray(), $null, $null, [string[]]@($Arguments.Keys))
}

$product = @{ word = 'Word'; excel = 'Excel'; powerpoint = 'PowerPoint' }[$App]
$curVer = (Get-ItemProperty "Registry::HKEY_CLASSES_ROOT\$product.Application\CurVer").'(default)'
$officeKey = "HKCU:\Software\Microsoft\Office\$(($curVer -split '\.')[-1]).0\$product"

# Se o motor já teve de encerrar um Office travado com este arquivo, o
# Office o marcou como "causou um erro grave" e perguntaria antes de abrir
# de novo (a pergunta ficaria esperando). Sai só a marca deste arquivo.
$disabled = "$officeKey\Resiliency\DisabledItems"
if (Test-Path $disabled) {
    $item = Get-Item $disabled
    foreach ($name in $item.GetValueNames()) {
        $value = $item.GetValue($name)
        if ($value -is [byte[]] -and
                [Text.Encoding]::Unicode.GetString($value).ToLower().Contains($InputPath.ToLower())) {
            Remove-ItemProperty $disabled -Name $name
        }
    }
}

# Office que este script abriu (não o que já estava aberto): o motor encerra
# esses processos se a conversão passar do tempo.
$exe = @{ word = 'WINWORD'; excel = 'EXCEL'; powerpoint = 'POWERPNT' }[$App]
$before = @(Get-Process $exe -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
function Write-NewPids {
    Get-Process $exe -ErrorAction SilentlyContinue |
        Where-Object { $before -notcontains $_.Id } |
        ForEach-Object { [Console]::Out.WriteLine("pid $($_.Id)") }
    [Console]::Out.Flush()
}

function Get-ExcelInput([string]$Path) {
    # CSV em UTF-8 sem BOM o Excel lê como ANSI e quebra os acentos: abre uma
    # cópia com BOM, na pasta de trabalho da saída (o motor apaga depois).
    if ($ext -ne 'csv') { return $Path }
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        return $Path
    }
    try {
        $text = (New-Object Text.UTF8Encoding -ArgumentList $false, $true).GetString($bytes)
    } catch {
        return $Path                                       # não é UTF-8: ANSI mesmo
    }
    $dir = Join-Path (Split-Path $OutputPath) 'entrada'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $copy = Join-Path $dir ([IO.Path]::GetFileName($Path))
    [IO.File]::WriteAllText($copy, $text, (New-Object Text.UTF8Encoding $true))
    return $copy
}

function Close-Office($Application, $Alerts, [int]$OpenDocuments) {
    $Application.DisplayAlerts = $Alerts
    if ($OpenDocuments -eq 0) { $Application.Quit() }
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($Application)
}

switch ($App) {
    'word' {
        $formats = @{ docx = 16; odt = 23; rtf = 6; doc = 0 }   # WdSaveFormat
        # Ao abrir PDF o Word pergunta "vai converter o PDF..." mesmo sem
        # alertas, e a pergunta fica esperando. A opção abaixo a dispensa; o
        # Word lê as opções ao iniciar, então ela vem antes do New-Object e
        # volta como estava no fim.
        $options = "$officeKey\Options"
        $pdfWarning = $null
        if ($ext -eq 'pdf') {
            if (-not (Test-Path $options)) { New-Item -Path $options -Force | Out-Null }
            $pdfWarning = (Get-ItemProperty $options -ErrorAction SilentlyContinue).DisableConvertPdfWarning
            Set-ItemProperty $options -Name DisableConvertPdfWarning -Value 1 -Type DWord
        }
        $word = New-Object -ComObject Word.Application
        Write-NewPids
        $alerts = $word.DisplayAlerts
        $doc = $null
        try {
            $word.DisplayAlerts = 0                               # wdAlertsNone
            $open = [ordered]@{
                FileName = $InputPath; ConfirmConversions = $false; ReadOnly = $true
                AddToRecentFiles = $false; PasswordDocument = $NoPassword
                Visible = $false; NoEncodingDialog = $true
            }
            if ($ext -eq 'txt') { $open.Encoding = 65001 }       # .txt em UTF-8
            $doc = Invoke-Com $word.Documents 'Open' $open
            if ($Format -eq 'pdf') {
                Invoke-Com $doc 'ExportAsFixedFormat' ([ordered]@{
                    OutputFileName = $OutputPath; ExportFormat = 17 })  # wdExportFormatPDF
            } else {
                $save = [ordered]@{ FileName = $OutputPath; AddToRecentFiles = $false }
                if ($Format -eq 'txt') {
                    $save.FileFormat = 2; $save.Encoding = 65001     # wdFormatText, UTF-8
                } else {
                    $save.FileFormat = $formats[$Format]
                }
                Invoke-Com $doc 'SaveAs2' $save
            }
        } finally {
            if ($doc) { Invoke-Com $doc 'Close' ([ordered]@{ SaveChanges = 0 }) }
            Close-Office $word $alerts $word.Documents.Count
            if ($ext -eq 'pdf') {
                if ($null -eq $pdfWarning) {
                    Remove-ItemProperty $options -Name DisableConvertPdfWarning -ErrorAction SilentlyContinue
                } else {
                    Set-ItemProperty $options -Name DisableConvertPdfWarning -Value $pdfWarning -Type DWord
                }
            }
        }
    }
    'excel' {
        $formats = @{ xlsx = 51; ods = 60; xls = 56 }              # XlFileFormat
        $excel = New-Object -ComObject Excel.Application
        Write-NewPids
        $alerts = $excel.DisplayAlerts
        $book = $null
        try {
            $excel.DisplayAlerts = $false
            $book = Invoke-Com $excel.Workbooks 'Open' ([ordered]@{
                Filename = (Get-ExcelInput $InputPath); UpdateLinks = 0; ReadOnly = $true
                Password = $NoPassword; AddToMru = $false })
            if ($Format -eq 'pdf') {
                $book.ExportAsFixedFormat(0, $OutputPath)          # xlTypePDF, todas as abas
            } elseif ($Format -eq 'csv') {
                try { $book.SaveAs($OutputPath, 62) }              # xlCSVUTF8 (Excel 2016+)
                catch { $book.SaveAs($OutputPath, 6) }             # xlCSV
            } else {
                $book.SaveAs($OutputPath, $formats[$Format])
            }
        } finally {
            if ($book) { $book.Close($false) }
            Close-Office $excel $alerts $excel.Workbooks.Count
        }
    }
    'powerpoint' {
        $formats = @{ pdf = 32; pptx = 24; odp = 35; ppt = 1 }    # PpSaveAsFileType
        $ppt = New-Object -ComObject PowerPoint.Application
        Write-NewPids
        $alerts = $ppt.DisplayAlerts
        $pres = $null
        try {
            $ppt.DisplayAlerts = 1                                 # ppAlertsNone
            $pres = Invoke-Com $ppt.Presentations 'Open' ([ordered]@{
                FileName = $InputPath; ReadOnly = -1; Untitled = 0; WithWindow = 0 })
            $pres.SaveAs($OutputPath, $formats[$Format])
        } finally {
            if ($pres) { $pres.Close() }
            Close-Office $ppt $alerts $ppt.Presentations.Count
        }
    }
}
if (-not (Test-Path -LiteralPath $OutputPath)) {
    [Console]::Error.WriteLine("o $App não gerou $OutputPath")
    exit 1
}
exit 0
