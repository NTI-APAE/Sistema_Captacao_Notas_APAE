from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions.chave_invalida_exception import ChaveInvalidaException
from app.domain.exceptions.execucao_nao_encontrada_exception import (
    ExecucaoNaoEncontradaException,
)
from app.domain.exceptions.nota_nao_encontrada_exception import (
    NotaNaoEncontradaException,
)
from app.domain.exceptions.pessoa_nao_encontrada_exception import (
    PessoaNaoEncontradaException,
)
from app.domain.exceptions.resultado_execucao_conflitante_exception import (
    ResultadoExecucaoConflitanteException,
)
from app.domain.exceptions.transicao_status_invalida_exception import (
    TransicaoStatusInvalidaException,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ChaveInvalidaException)
    async def chave_invalida_handler(
        request: Request,
        exc: ChaveInvalidaException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "code": "CHAVE_INVALIDA"},
        )

    @app.exception_handler(NotaNaoEncontradaException)
    async def nota_nao_encontrada_handler(
        request: Request,
        exc: NotaNaoEncontradaException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "code": "NOTA_NAO_ENCONTRADA"},
        )

    @app.exception_handler(PessoaNaoEncontradaException)
    async def pessoa_nao_encontrada_handler(
        request: Request,
        exc: PessoaNaoEncontradaException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "code": "PESSOA_NAO_ENCONTRADA"},
        )

    @app.exception_handler(ExecucaoNaoEncontradaException)
    async def execucao_nao_encontrada_handler(
        request: Request,
        exc: ExecucaoNaoEncontradaException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "code": "EXECUCAO_NAO_ENCONTRADA"},
        )

    @app.exception_handler(TransicaoStatusInvalidaException)
    async def transicao_invalida_handler(
        request: Request,
        exc: TransicaoStatusInvalidaException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "code": "TRANSICAO_STATUS_INVALIDA"},
        )

    @app.exception_handler(ResultadoExecucaoConflitanteException)
    async def resultado_conflitante_handler(
        request: Request,
        exc: ResultadoExecucaoConflitanteException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "code": "RESULTADO_EXECUCAO_CONFLITANTE"},
        )
