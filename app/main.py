import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.routes.webhook import router as webhook_router

# Configurar logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management para la aplicación"""
    # Startup
    logger.info("Creando tablas en BD...")
    Base.metadata.create_all(bind=engine)
    logger.info("Aplicación iniciada")
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación")


def create_app() -> FastAPI:
    """Factory para crear la aplicación FastAPI"""
    
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(webhook_router)

    return app


app = create_app()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "nombre": settings.api_title,
        "version": settings.api_version,
        "estado": "activo",
    }
