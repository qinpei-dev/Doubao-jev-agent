from fastapi import FastAPI
from .config import settings
from .core.decision import DecisionEngine
from .jev.mock import MockJEVClient
from .jev.http import HTTPJEVClient
from .api.routes import build_router


def create_app() -> FastAPI:
    if settings.jev_mode == "mock":
        client = MockJEVClient()
    elif settings.jev_mode == "real":
        client = HTTPJEVClient(settings.jev_api_url, settings.jev_api_key)
    else:
        raise RuntimeError("JEV_MODE must be 'mock' or 'real'")
    app = FastAPI(title="Doubao JEV Agent", version="0.1.0", description="LLM generates. JEV decides.")
    app.include_router(build_router(DecisionEngine(client)))
    return app


app = create_app()
