"""Compatibilidade com o comando antigo: uvicorn teste_webhook:app."""

if __package__:
    pass
else:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
