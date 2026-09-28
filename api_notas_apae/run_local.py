"""Inicia a API local sem carregar as configurações de banco da Evolution."""

import os
from pathlib import Path

import uvicorn
from dotenv import dotenv_values, load_dotenv


def main():
    project = Path(__file__).resolve().parent
    load_dotenv(project / ".env", override=False)
    if not (os.getenv("NOTAS_INTERNAL_API_KEY") or os.getenv("WEBHOOK_TOKEN")):
        # Somente leitura, somente o segredo de integração, nunca DATABASE_URL.
        integration = dotenv_values(project.parent / "EvolutionAPI" / ".env")
        token = integration.get("NOTAS_INTERNAL_API_KEY") or integration.get(
            "WEBHOOK_TOKEN"
        )
        if token:
            os.environ["NOTAS_INTERNAL_API_KEY"] = token
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
