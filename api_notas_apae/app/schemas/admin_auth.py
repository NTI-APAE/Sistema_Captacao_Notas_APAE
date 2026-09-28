from pydantic import BaseModel, EmailStr, Field


class LoginAdminRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=200)


class UsuarioAdminResponse(BaseModel):
    nome: str
    email: EmailStr
    role: str
    scopes: list[str]
