$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistRoot = Join-Path $Root "dist"
$ZipPath = Join-Path $DistRoot "Leitor Nota Fiscal - Com Venv.zip"
$SpecPath = Join-Path $Root "Leitor Nota Fiscal.spec"
$RequirementsPath = Join-Path $Root "requirements.txt"
$ProjectVenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$BuildStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$PackageRoot = Join-Path $DistRoot "pacote_temp_$BuildStamp"
$DistDir = Join-Path $PackageRoot "Leitor Nota Fiscal"

function Get-Python {
    if (Test-Path -LiteralPath $ProjectVenvPython) {
        return $ProjectVenvPython
    }
    return "python"
}

function Get-PlaywrightBrowsersSource {
    $candidates = @()
    if ($env:PLAYWRIGHT_BROWSERS_PATH) {
        $candidates += $env:PLAYWRIGHT_BROWSERS_PATH
    }
    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA "ms-playwright")
    }
    $candidates += (Join-Path $Root "ms-playwright")

    foreach ($candidate in $candidates) {
        if (-not $candidate) {
            continue
        }
        if ((Test-Path -LiteralPath $candidate) -and (Get-ChildItem -LiteralPath $candidate -Directory -Filter "chromium-*" -ErrorAction SilentlyContinue)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Copy-ProjectSources {
    $files = @(
        "main.py",
        "gui.py",
        "database.py",
        "models.py",
        "leitor_txt.py",
        "automacao_notalegal.py",
        "api_client.py",
        "relatorios.py",
        "config.py",
        "requirements.txt",
        "README.md"
    )

    foreach ($file in $files) {
        $source = Join-Path $Root $file
        if (Test-Path -LiteralPath $source) {
            Copy-Item -LiteralPath $source -Destination $DistDir -Force
        }
    }

    $assetsSource = Join-Path $Root "assets"
    $assetsDest = Join-Path $DistDir "assets"
    if (Test-Path -LiteralPath $assetsSource) {
        if (Test-Path -LiteralPath $assetsDest) {
            Remove-Item -LiteralPath $assetsDest -Recurse -Force
        }
        Copy-Item -LiteralPath $assetsSource -Destination $assetsDest -Recurse -Force
    }
}

function Write-LaunchersAndInstructions {
    $venvBat = Join-Path $DistDir "Executar pelo venv.bat"
    @"
@echo off
cd /d "%~dp0"
set "PLAYWRIGHT_BROWSERS_PATH=%~dp0ms-playwright"
"%~dp0venv\Scripts\python.exe" "%~dp0main.py"
pause
"@ | Set-Content -LiteralPath $venvBat -Encoding ASCII

    $instructions = Join-Path $DistDir "INSTRUCOES_INSTALACAO.txt"
    @"
Para instalar em outra maquina:

1. Extraia o ZIP inteiro antes de executar.
2. Abra "Leitor Nota Fiscal.exe".
3. Nao mova somente o .exe; ele precisa das pastas _internal, logs e ms-playwright.

Opcional:

- A pasta venv tambem vai no ZIP com as dependencias Python instaladas.
- Se a maquina tiver Python compativel, voce pode testar pelo arquivo "Executar pelo venv.bat".
- Para uso normal, prefira o "Leitor Nota Fiscal.exe".

Observacoes:

- A aplicacao usa a API central configurada em NOTAS_API_URL.
- Os logs ficam em logs\sistema.log.
- A pasta ms-playwright contem o Chromium usado pela automacao.
"@ | Set-Content -LiteralPath $instructions -Encoding UTF8
}

function Remove-PackagedDatabases {
    $databaseNames = @("notas.db", "notas.sqlite", "notas.sqlite3")
    Get-ChildItem -LiteralPath $DistDir -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $databaseNames -contains $_.Name.ToLowerInvariant() } |
        ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Force
        }
}

$Python = Get-Python
New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null

Write-Host "Compilando arquivos Python..."
& $Python -m py_compile main.py gui.py database.py models.py leitor_txt.py automacao_notalegal.py api_client.py relatorios.py config.py teste_cadastro_direto.py

Write-Host "Gerando executavel com PyInstaller..."
& $Python -m PyInstaller --noconfirm --distpath $PackageRoot $SpecPath

if (-not (Test-Path -LiteralPath $DistDir)) {
    throw "A pasta de distribuicao nao foi criada: $DistDir"
}

Write-Host "Copiando Chromium do Playwright..."
$BrowserSource = Get-PlaywrightBrowsersSource
if (-not $BrowserSource) {
    Write-Host "Chromium nao encontrado localmente. Instalando pelo Playwright..."
    & $Python -m playwright install chromium
    $BrowserSource = Get-PlaywrightBrowsersSource
}
if (-not $BrowserSource) {
    throw "Nao foi possivel localizar a pasta ms-playwright com Chromium."
}

$BrowserDest = Join-Path $DistDir "ms-playwright"
if (Test-Path -LiteralPath $BrowserDest) {
    Remove-Item -LiteralPath $BrowserDest -Recurse -Force
}
Copy-Item -LiteralPath $BrowserSource -Destination $BrowserDest -Recurse -Force

New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "logs") | Out-Null

Write-Host "Copiando codigo-fonte para execucao opcional pelo venv..."
Copy-ProjectSources

Write-Host "Removendo bancos locais que nao devem ir no pacote..."
Remove-PackagedDatabases

Write-Host "Criando venv dentro da distribuicao..."
$VenvDir = Join-Path $DistDir "venv"
if (Test-Path -LiteralPath $VenvDir) {
    Remove-Item -LiteralPath $VenvDir -Recurse -Force
}
& $Python -m venv $VenvDir --copies
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $RequirementsPath

Write-LaunchersAndInstructions

Write-Host "Compactando ZIP final..."
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path $DistDir -DestinationPath $ZipPath -Force

try {
    Remove-Item -LiteralPath $PackageRoot -Recurse -Force
} catch {
    Write-Host "Nao foi possivel remover a pasta temporaria: $PackageRoot"
}

Write-Host ""
Write-Host "ZIP gerado com sucesso:"
Write-Host $ZipPath
