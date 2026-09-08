param([switch]$Offline)

$ErrorActionPreference = "Stop"
$networkArgs = if ($Offline) { @("--offline") } else { @() }

function Invoke-CheckedNative {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Native command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$projectRoot = Split-Path -Parent $PSScriptRoot
$smokeRoot = Join-Path $projectRoot ".tmp\installed-package-smoke"
$wheelVenv = Join-Path $smokeRoot "wheel-venv"
$sdistVenv = Join-Path $smokeRoot "sdist-venv"
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

$wheel = Get-ChildItem -LiteralPath $dist -Filter "agent_image-*.whl" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $wheel) {
    throw "No agent-image wheel found under dist/. Run 'uv build' first."
}
$sdist = Get-ChildItem -LiteralPath $dist -Filter "agent_image-*.tar.gz" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $sdist) {
    throw "No agent-image sdist found under dist/. Run 'uv build' first."
}

Invoke-CheckedNative { uv venv @networkArgs --cache-dir $uvCache --python 3.12 $wheelVenv }
$wheelPython = Join-Path $wheelVenv "Scripts\python.exe"
$wheelAgentImage = Join-Path $wheelVenv "Scripts\agent-image.exe"

Invoke-CheckedNative { uv pip install @networkArgs --cache-dir $uvCache --python $wheelPython $wheel.FullName }
Invoke-CheckedNative { & $wheelAgentImage --help | Out-Null }
Invoke-CheckedNative { & $wheelPython -m agent_image --help | Out-Null }
Invoke-CheckedNative { & $wheelPython -c "from importlib.metadata import distribution; import agent_image; assert distribution('agent-image').metadata['Name'] == 'agent-image'; print(agent_image.__version__)" }

$fixture = Join-Path $projectRoot "tests\fixtures\minimal"
$privateImage = Join-Path $smokeRoot "installed-private.aimg"
$publicImage = Join-Path $smokeRoot "installed-public.aimg"
Invoke-CheckedNative { & $wheelPython -c "from pathlib import Path; from agent_image.service import build_fixture_image; build_fixture_image(Path(r'$fixture'), Path(r'$privateImage'), policy='private')" }
Invoke-CheckedNative { & $wheelAgentImage inspect $privateImage --json | Out-Null }
Invoke-CheckedNative { & $wheelAgentImage verify $privateImage --json | Out-Null }
Invoke-CheckedNative { & $wheelAgentImage redact $privateImage --policy public --output $publicImage --json | Out-Null }
Invoke-CheckedNative { & $wheelAgentImage diff $privateImage $publicImage --json | Out-Null }
Invoke-CheckedNative { & $wheelAgentImage registry validate (Join-Path $projectRoot "registry\v0.1\index.json") --json | Out-Null }

Invoke-CheckedNative { uv venv @networkArgs --cache-dir $uvCache --python 3.12 $sdistVenv }
$sdistPython = Join-Path $sdistVenv "Scripts\python.exe"
$sdistAgentImage = Join-Path $sdistVenv "Scripts\agent-image.exe"
Invoke-CheckedNative { uv pip install @networkArgs --cache-dir $uvCache --python $sdistPython $sdist.FullName }
Invoke-CheckedNative { & $sdistAgentImage --help | Out-Null }
Invoke-CheckedNative { & $sdistAgentImage verify $privateImage --json | Out-Null }
Invoke-CheckedNative { & $sdistPython -c "from importlib.metadata import distribution; import agent_image; assert distribution('agent-image').metadata['Name'] == 'agent-image'; print(agent_image.__version__)" }
