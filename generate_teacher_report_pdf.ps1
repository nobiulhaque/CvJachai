param(
    [string]$InputFile = "teacher_report.txt",
    [string]$OutputFile = "teacher_report.pdf"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Escape-PdfText {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    $escaped = $Text.Replace("\", "\\")
    $escaped = $escaped.Replace("(", "\(")
    $escaped = $escaped.Replace(")", "\)")
    return $escaped
}

function Wrap-TextLine {
    param(
        [string]$Line,
        [int]$MaxWidth = 92
    )

    if ([string]::IsNullOrWhiteSpace($Line)) {
        return @("")
    }

    if ($Line.Length -le $MaxWidth) {
        return @($Line)
    }

    $words = $Line -split '\s+'
    $wrapped = New-Object System.Collections.Generic.List[string]
    $current = ""

    foreach ($word in $words) {
        if ([string]::IsNullOrEmpty($current)) {
            $current = $word
            continue
        }

        $candidate = "$current $word"
        if ($candidate.Length -le $MaxWidth) {
            $current = $candidate
        } else {
            $wrapped.Add($current)
            $current = $word
        }
    }

    if (-not [string]::IsNullOrEmpty($current)) {
        $wrapped.Add($current)
    }

    return $wrapped
}

if (-not (Test-Path -LiteralPath $InputFile)) {
    throw "Input file not found: $InputFile"
}

$rawLines = Get-Content -LiteralPath $InputFile -Encoding UTF8
$lines = New-Object System.Collections.Generic.List[string]

foreach ($line in $rawLines) {
    $wrapped = Wrap-TextLine -Line $line
    foreach ($wrappedLine in $wrapped) {
        $lines.Add($wrappedLine)
    }
}

$linesPerPage = 44
$pages = New-Object System.Collections.Generic.List[object]

for ($i = 0; $i -lt $lines.Count; $i += $linesPerPage) {
    $end = [Math]::Min($i + $linesPerPage - 1, $lines.Count - 1)
    $pageLines = $lines[$i..$end]
    $pages.Add($pageLines)
}

$pageCount = $pages.Count
$fontObjectNumber = 3 + (2 * $pageCount)
$objects = New-Object System.Collections.Generic.List[string]

$objects.Add("<< /Type /Catalog /Pages 2 0 R >>")

$kidRefs = for ($i = 0; $i -lt $pageCount; $i++) {
    "{0} 0 R" -f (3 + ($i * 2))
}
$objects.Add("<< /Type /Pages /Kids [ $($kidRefs -join ' ') ] /Count $pageCount >>")

for ($pageIndex = 0; $pageIndex -lt $pageCount; $pageIndex++) {
    $pageObjectNumber = 3 + ($pageIndex * 2)
    $contentObjectNumber = $pageObjectNumber + 1
    $pageLines = [string[]]$pages[$pageIndex]

    $streamLines = New-Object System.Collections.Generic.List[string]
    $streamLines.Add("BT")
    $streamLines.Add("/F1 10 Tf")
    $streamLines.Add("14 TL")
    $streamLines.Add("50 760 Td")

    foreach ($line in $pageLines) {
        $escaped = Escape-PdfText $line
        $streamLines.Add("($escaped) Tj")
        $streamLines.Add("T*")
    }

    $footer = "Page {0} of {1}" -f ($pageIndex + 1), $pageCount
    $streamLines.Add("T*")
    $streamLines.Add("($footer) Tj")
    $streamLines.Add("ET")

    $streamData = $streamLines -join "`n"
    $streamBytes = [System.Text.Encoding]::ASCII.GetBytes($streamData)
    $streamLength = $streamBytes.Length

    $objects.Add("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 $fontObjectNumber 0 R >> >> /Contents $contentObjectNumber 0 R >>")
    $objects.Add("<< /Length $streamLength >>`nstream`n$streamData`nendstream")
}

$objects.Add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

$builder = New-Object System.Text.StringBuilder
[void]$builder.Append("%PDF-1.4`n")

$offsets = New-Object System.Collections.Generic.List[int]
$offsets.Add(0)

for ($i = 0; $i -lt $objects.Count; $i++) {
    $objectNumber = $i + 1
    $offsets.Add($builder.Length)
    [void]$builder.Append("$objectNumber 0 obj`n")
    [void]$builder.Append($objects[$i])
    [void]$builder.Append("`nendobj`n")
}

$xrefStart = $builder.Length
[void]$builder.Append("xref`n")
[void]$builder.Append("0 $($objects.Count + 1)`n")
[void]$builder.Append("0000000000 65535 f `n")

for ($i = 1; $i -le $objects.Count; $i++) {
    $offset = $offsets[$i]
    [void]$builder.Append(("{0:d10} 00000 n `n" -f $offset))
}

[void]$builder.Append("trailer`n")
[void]$builder.Append("<< /Size $($objects.Count + 1) /Root 1 0 R >>`n")
[void]$builder.Append("startxref`n")
[void]$builder.Append("$xrefStart`n")
[void]$builder.Append("%%EOF")

[System.IO.File]::WriteAllBytes(
    (Join-Path (Get-Location) $OutputFile),
    [System.Text.Encoding]::ASCII.GetBytes($builder.ToString())
)

Write-Output "Created PDF: $OutputFile"
