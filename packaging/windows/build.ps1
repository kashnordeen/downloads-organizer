param(
    [Parameter(Mandatory=$true)][string]$Python,
    [string]$MakeAppx,
    [string]$Publisher = 'CN=LocalOrganizer',
    [string]$Output = (Join-Path $PSScriptRoot '..\..\dist')
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$outputRoot = [IO.Path]::GetFullPath($Output)
Push-Location $projectRoot
$buildPath = $env:PATH
try {
    # Avoid unrelated DLLs exported by other development tools.
    $env:PATH = (Split-Path -Parent $Python) + ';' + $env:SystemRoot + '\System32;' + $env:SystemRoot
    & $Python -m PyInstaller --noconfirm --distpath $outputRoot --workpath (Join-Path $projectRoot 'build') (Join-Path $PSScriptRoot 'bundle.spec')
    if ($LASTEXITCODE -ne 0) { throw 'Bundle build failed' }
    $bundle = Join-Path $outputRoot 'DownloadsOrganizer'
    Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination $bundle
    Copy-Item -LiteralPath (Join-Path $projectRoot 'THIRD_PARTY.md') -Destination $bundle
    Copy-Item -LiteralPath (Join-Path $projectRoot 'licenses') -Destination $bundle -Recurse -Force
    if ($MakeAppx) {
        # Each run uses fresh staging so removed files cannot leak into a package.
        $stage = Join-Path $projectRoot ('build\msix-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $stage | Out-Null
        Get-ChildItem -LiteralPath $bundle | Copy-Item -Destination $stage -Recurse
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Assets') -Destination $stage -Recurse
        [xml]$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'AppxManifest.xml') -Raw
        $manifest.Package.Identity.Publisher = $Publisher
        $manifest.Save((Join-Path $stage 'AppxManifest.xml'))
        & $MakeAppx pack /d $stage /p (Join-Path $outputRoot 'DownloadsOrganizer-0.1.0-x64-unsigned.msix') /o *> (Join-Path $projectRoot 'build\makeappx.log')
        if ($LASTEXITCODE -ne 0) { throw 'MSIX validation/packing failed' }
        Get-Content -LiteralPath (Join-Path $projectRoot 'build\makeappx.log') -Tail 3
    }
    Compress-Archive -LiteralPath $bundle -DestinationPath (Join-Path $outputRoot 'DownloadsOrganizer-0.1.0-windows-x64.zip') -Force
} finally { $env:PATH = $buildPath; Pop-Location }
