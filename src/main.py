from fastapi import FastAPI
from .core.decision import DecisionEngine
from .jev.client import JEVClient
from .api.routes import build_router


def create_app() -> FastAPI:
    client = JEVClient.from_env()
    app = FastAPI(title="Doubao JEV Agent", version="0.1.0", description="LLM generates. JEV decides.")
    app.include_router(build_router(DecisionEngine(client)))
    return app


app = create_app()
