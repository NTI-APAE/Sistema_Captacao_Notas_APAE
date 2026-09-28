import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_migration_aditiva_preserva_dados(tmp_path):
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/202609210001_eventos_imagem.py"
    )
    spec = importlib.util.spec_from_file_location("migration_eventos", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE dados_existentes (valor TEXT)"))
        connection.execute(text("INSERT INTO dados_existentes VALUES ('preservado')"))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            module.upgrade()
        assert (
            connection.scalar(text("SELECT valor FROM dados_existentes"))
            == "preservado"
        )
        assert inspect(connection).get_pk_constraint("eventos_imagem")[
            "constrained_columns"
        ] == ["origem", "instancia", "evento_id"]
    engine.dispose()
