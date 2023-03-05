import logging

import fastapi
from fastapi.responses import PlainTextResponse

from app.config import settings


logger = logging.getLogger(settings.logger_name)


def create_app():
    app = fastapi.FastAPI(
        title=settings.app_name,
    )

    @app.get("/")
    async def root():
        return PlainTextResponse("OK")

    # Router
    from app.api.router import router

    app.include_router(router, prefix=f"/channel")

    return app


app = create_app()