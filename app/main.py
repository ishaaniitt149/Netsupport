"""Network Operations Intelligence & Predictive Maintenance Platform (NOIPMP)

Application entry point, FastAPI instance, and CLI bootstrap.
"""

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Initializing %s in [%s] mode...", settings.app_name, settings.app_env.value)
    logger.info("Synthetic Simulation Seed: %d", settings.simulation_seed)
    logger.info("LLM Provider Configured: %s", settings.llm_provider.value)
    yield
    logger.info("Shutting down %s...", settings.app_name)


def create_app() -> FastAPI:
    """Application factory for FastAPI instance."""
    settings = get_settings()
    application = FastAPI(
        title="Network Operations Intelligence & Predictive Maintenance Platform",
        description="Production-shaped prototype for automated Cisco network triage and predictive maintenance.",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Enable CORS for local developer dashboards
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()


def cli_entrypoint() -> None:
    """CLI entrypoint for running the platform directly."""
    import uvicorn

    settings = get_settings()
    logger.info("Starting web server on %s:%d", settings.app_host, settings.app_port)
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        from app.api.health import get_health

        health = get_health()
        print(health.model_dump_json(indent=2))
    else:
        cli_entrypoint()
