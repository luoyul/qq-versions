[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateSet('qq')]
    [string] $Product,

    [string[]] $Versions,

    [switch] $All,

    [switch] $ListOnly
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repoRoot = Split-Path -Parent $PSScriptRoot
$historyUrl = 'https://www.7723.cn/apps/59723/history'
$catalogPath = Join-Path $repoRoot 'catalog\qq.json'

if (-not $All -and (-not $Versions -or $Versions.Count -eq 0)) {
    throw 'Specify -Versions (for example 9.3.75,9.3.70) or use -All.'
}

function Get-Page([string] $url) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -MaximumRedirection 5
    return $response.Content
}

function Get-HistoryEntries([string] $html) {
    $options = [Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [Text.RegularExpressions.RegexOptions]::Singleline
    $pattern = '<li[^>]*class=["''][^"'']*public-history_item[^"'']*["''][^>]*>.*?<span[^>]*class=["''][^"'']*public-hostory_title[^"'']*["''][^>]*>\s*QQ\s*v?([^<\s]+).*?</span>.*?<span[^>]*class=["''][^"'']*public-hostory_text[^"'']*["''][^>]*>\s*v?([^&<\s]+).*?([0-9.]+MB).*?</span>.*?<a[^>]*href=["'']([^"'']*history-\d+)["'']'
    foreach ($match in [regex]::Matches($html, $pattern, $options)) {
        [pscustomobject]@{
            Version = $match.Groups[1].Value.Trim()
            SizeText = $match.Groups[3].Value.Trim()
            DetailUrl = [uri]::new([uri]$historyUrl, $match.Groups[4].Value).AbsoluteUri
        }
    }
}

function Get-DownloadUrl([string] $detailUrl) {
    $html = Get-Page $detailUrl
    $options = [Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [Text.RegularExpressions.RegexOptions]::Singleline
    $matches = [regex]::Matches($html, 'href=["''](https?://[^"'']+\.apk(?:\?[^"'']*)?)["'']', $options)
    $url = $matches | Select-Object -First 1 | ForEach-Object { $_.Groups[1].Value }
    if (-not $url) { throw "No APK download URL found: $detailUrl" }
    return $url
}

if (Test-Path $catalogPath) {
    $catalog = Get-Content -Raw $catalogPath | ConvertFrom-Json
} else {
    $catalog = [pscustomobject]@{ product = 'qq'; packageName = 'com.tencent.mobileqq'; versions = @() }
}

$entries = @(Get-HistoryEntries (Get-Page $historyUrl))
if (-not $entries) { throw 'No QQ history entries found.' }

$wanted = if ($All) { $entries } else {
    foreach ($version in $Versions) {
        $entry = $entries | Where-Object { $_.Version -eq $version } | Select-Object -First 1
        if (-not $entry) { Write-Warning "Version not found on 7723: $version"; continue }
        $entry
    }
}

foreach ($entry in $wanted) {
    $fileName = "QQ$($entry.Version).apk"
    $filePath = Join-Path $repoRoot $fileName
    if ($ListOnly) {
        [pscustomobject]@{ Version = $entry.Version; DetailUrl = $entry.DetailUrl; File = $fileName }
        continue
    }

    $downloadUrl = Get-DownloadUrl $entry.DetailUrl
    if (Test-Path $filePath) {
        $item = Get-Item $filePath
        if ($item.Length -gt 0) {
            Write-Host "Skip existing $fileName ($([math]::Round($item.Length / 1MB, 2)) MB)"
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $filePath).Hash.ToLowerInvariant()
        } else {
            Remove-Item -LiteralPath $filePath -Force
            $hash = $null
        }
    } else {
        $hash = $null
    }

    if (-not $hash -and $PSCmdlet.ShouldProcess($filePath, "Download $downloadUrl")) {
        $partPath = "$filePath.partial"
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $partPath
            Move-Item -LiteralPath $partPath -Destination $filePath -Force
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $filePath).Hash.ToLowerInvariant()
        } finally {
            if (Test-Path $partPath) { Remove-Item -LiteralPath $partPath -Force -ErrorAction SilentlyContinue }
        }
    }

    if ($hash) {
        $record = [pscustomobject]@{
            product = 'qq'
            packageName = 'com.tencent.mobileqq'
            versionName = $entry.Version
            fileName = $fileName
            size = (Get-Item -LiteralPath $filePath).Length
            sha256 = $hash
            sourcePage = $entry.DetailUrl
            downloadedAt = (Get-Date).ToUniversalTime().ToString('o')
        }
        $existing = @($catalog.versions | Where-Object { $_.versionName -ne $entry.Version })
        $catalog.versions = @($existing + $record | Sort-Object @{ Expression = { [version]$_.versionName }; Descending = $true })
    }
}

if (-not $ListOnly) {
    $catalog | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 -LiteralPath $catalogPath
    Write-Host "Catalog updated: $catalogPath"
}
