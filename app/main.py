import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.rag.qdrant_store import ensure_collection

# Ensure application logs (app.*) are emitted to stdout/stderr so they show in `docker logs`.
# uvicorn only configures its own loggers; without this, app INFO/DEBUG never surface.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("TESTING"):
        ensure_collection()

    crawler_task: asyncio.Task | None = None
    if settings.crawler_enabled and not os.getenv("TESTING"):
        from app.crawler.scheduler import run_scheduler_loop

        crawler_task = asyncio.create_task(run_scheduler_loop())
        logger.info("BabaAI crawler scheduler started")

    yield

    if crawler_task is not None:
        crawler_task.cancel()
        try:
            await crawler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="BabaAI AI Service",
    description="LLM agents, RAG, and crawler for BabaAI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(AppError)
async def app_exception_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.message})


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "BabaAI AI Service", "docs": "/docs"}
