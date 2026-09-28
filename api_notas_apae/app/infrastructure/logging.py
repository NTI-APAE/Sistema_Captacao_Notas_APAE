import logging
import re


class RedactAccessPath(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # O access log padrão inclui chaves/telefones dos GETs públicos.
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            path = str(args[2]).split("?", 1)[0]
            args[2] = re.sub(
                r"(/notas/chave/|/pessoas/telefone/)[^/]+",
                r"\1[redacted]",
                path,
            )
            record.args = tuple(args)
        return True


def configure_logging(level: str) -> None:
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactAccessPath) for f in access.filters):
        access.addFilter(RedactAccessPath())
    # Clientes HTTP em INFO imprimem URLs que podem conter dados pessoais.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s %(levelname)s service=api-notas-apae "
            "operation=%(name)s message=%(message)s"
        ),
    )
