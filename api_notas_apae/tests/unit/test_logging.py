import logging

from app.infrastructure.logging import RedactAccessPath


def test_remove_chave_telefone_e_query_do_access_log():
    for path in [
        "/notas/chave/123456?token=segredo",
        "/pessoas/telefone/5598999999999",
    ]:
        record = logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            "",
            0,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1", "GET", path, "1.1", 200),
            None,
        )
        assert RedactAccessPath().filter(record)
        assert "[redacted]" in record.getMessage()
        assert "123456" not in record.getMessage()
        assert "5598999999999" not in record.getMessage()
        assert "segredo" not in record.getMessage()
