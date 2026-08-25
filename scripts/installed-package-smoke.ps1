$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$projectRoot = Split-Path -Parent $PSScriptRoot
$smokeRoot = Join-Path $projectRoot ".tmp\installed-package-smoke"
$venv = Join-Path $smokeRoot ".venv"
$dist = Join-Path $projectRoot "dist"
$uvCache = Join-Path $projectRoot ".tmp\uv-cache"
$resolvedProjectRoot = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\') + '\'
$resolvedSmokeRoot = [System.IO.Path]::GetFullPath($smokeRoot)

if (-not $resolvedSmokeRoot.StartsWith($resolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $resolvedSmokeRoot) -ne "installed-package-smoke") {
    throw "Refusing to clean an unexpected smoke-test directory: $resolvedSmokeRoot"
}

if (Test-Path -LiteralPath $smokeRoot) {
    Remove-Item -LiteralPath $smokeRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $smokeRoot | Out-Null

$wheel = Get-ChildItem -LiteralPath $dist -Filter "open_agent_image-*.whl" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $wheel) {
    throw "No open-agent-image wheel found under dist/. Run 'uv build' first."
}

uv venv --offline --cache-dir $uvCache --python 3.12 $venv
$python = Join-Path $venv "Scripts\python.exe"
$agentImage = Join-Path $venv "Scripts\agent-image.exe"

uv pip install --offline --cache-dir $uvCache --python $python $wheel.FullName
& $agentImage --help | Out-Null
& $python -m agent_image --help | Out-Null
& $python -c "import agent_image; print(agent_image.__version__)"
