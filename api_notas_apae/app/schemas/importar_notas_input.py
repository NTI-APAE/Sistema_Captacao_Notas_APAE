from pydantic import BaseModel, Field


class ImportarNotasTxtRequest(BaseModel):
    nome_arquivo: str = Field(min_length=1, max_length=255)
    total_linhas: int = Field(ge=0)
    total_invalidas: int = Field(ge=0)
    total_duplicadas_txt: int = Field(ge=0)
    chaves: list[str] = Field(max_length=5000)


class ImportarNotasTxtResponse(BaseModel):
    total_linhas: int
    total_validas: int
    total_invalidas: int
    total_duplicadas: int
    total_inseridas: int
    total_reativadas: int
    total_ja_existentes: int
