from fastapi import FastAPI

from app.infrastructure.config import get_settings
from app.infrastructure.exception_handlers import register_exception_handlers
from app.infrastructure.logging import configure_logging
from app.routes.admin_auth_routes import router as admin_auth_router
from app.routes.admin_reporting_routes import router as admin_reporting_router
from app.routes.health_routes import router as health_router
from app.routes.imagens import router as imagens_router
from app.routes.notas_routes import router as notas_router
from app.routes.pessoas_routes import router as pessoas_router
from app.routes.submissao_routes import (
    router as submissao_router,
)
from app.routes.worker_routes import router as worker_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="API Notas APAE",
        version="0.1.0",
        description="Backend em camadas para captacao de notas fiscais.",
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(submissao_router)
    app.include_router(imagens_router)
    app.include_router(notas_router)
    app.include_router(pessoas_router)
    app.include_router(worker_router)
    app.include_router(admin_auth_router)
    app.include_router(admin_reporting_router)
    return app


app = create_app()
