"""Dependências das consultas administrativas de leitura."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_session
from app.repositories.admin_reporting_repository import AdminReportingRepository
from app.schemas.admin_reporting_filters import AdminReportingFilter
from app.services.admin_reporting_service import AdminReportingService


def get_admin_reporting_service(session: Annotated[Session, Depends(get_session)]):
    return AdminReportingService(AdminReportingRepository(session))


def get_filtro(request: Request):
    try:
        return AdminReportingFilter.model_validate(dict(request.query_params))
    except ValidationError as error:
        raise HTTPException(
            422, "Filtros inválidos. Confira as datas e os valores."
        ) from error
