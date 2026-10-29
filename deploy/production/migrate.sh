#!/usr/bin/env sh
set -eu

production_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
env_file="$production_dir/production.env"
evolution_env_file="$production_dir/evolution-api.env"
compose_file="$production_dir/docker-compose.yml"

test -f "$env_file" || {
  echo "Crie deploy/production/production.env a partir de production.env.example." >&2
  exit 1
}
test -f "$evolution_env_file" || {
  echo "Crie deploy/production/evolution-api.env a partir de evolution-api.env.example." >&2
  exit 1
}

if grep -q 'REPLACE_WITH_' "$env_file" "$evolution_env_file"; then
  echo "Substitua todos os placeholders REPLACE_WITH_* antes da migration." >&2
  exit 1
fi

docker compose --env-file "$env_file" -f "$compose_file" config --quiet
docker compose --env-file "$env_file" -f "$compose_file" --profile migration run --rm migrate
