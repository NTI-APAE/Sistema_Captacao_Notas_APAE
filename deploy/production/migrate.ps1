$ErrorActionPreference = "Stop"

$productionDir = $PSScriptRoot
$envFile = Join-Path $productionDir "production.env"
$evolutionEnvFile = Join-Path $productionDir "evolution-api.env"
$composeFile = Join-Path $productionDir "docker-compose.yml"

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Crie deploy/production/production.env a partir de production.env.example."
}

if (-not (Test-Path -LiteralPath $evolutionEnvFile)) {
    throw "Crie deploy/production/evolution-api.env a partir de evolution-api.env.example."
}

$configuredFiles = Get-Content -LiteralPath $envFile, $evolutionEnvFile -Raw
if ($configuredFiles -match "REPLACE_WITH_") {
    throw "Substitua todos os placeholders REPLACE_WITH_* antes da migration."
}

docker compose --env-file $envFile -f $composeFile config --quiet
docker compose --env-file $envFile -f $composeFile --profile migration run --rm migrate
