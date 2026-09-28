import argparse
import getpass
from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.infrastructure.admin_auth import normalizar_email, password_hash
from app.models.usuario_admin_model import UsuarioAdminModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria ou atualiza um administrador")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("ADMIN", "LEITURA"), default="ADMIN")
    args = parser.parse_args()
    senha = getpass.getpass("Senha (mínimo 12 caracteres): ")
    confirmacao = getpass.getpass("Confirme a senha: ")
    if senha != confirmacao:
        raise SystemExit("As senhas não coincidem.")
    if len(senha) < 12:
        raise SystemExit("A senha deve ter no mínimo 12 caracteres.")

    email = normalizar_email(args.email)
    with SessionLocal() as session:
        usuario = session.scalar(
            select(UsuarioAdminModel).where(UsuarioAdminModel.email == email)
        )
        if usuario is None:
            usuario = UsuarioAdminModel(
                id=uuid4(),
                nome=args.nome.strip(),
                email=email,
                senha_hash=password_hash.hash(senha),
                role=args.role,
                ativo=True,
            )
            session.add(usuario)
            action = "criado"
        else:
            usuario.nome = args.nome.strip()
            usuario.senha_hash = password_hash.hash(senha)
            usuario.role = args.role
            usuario.ativo = True
            action = "atualizado"
        session.commit()
    print(f"Administrador {action}: {email}, Senha: {senha}")


if __name__ == "__main__":
    main()
