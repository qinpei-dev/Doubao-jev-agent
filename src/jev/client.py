from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
from ..core.models import DecisionRequest, DecisionResult


class JEVClient(ABC):
    """Common interface and environment-aware factory for JEV clients."""

    @classmethod
    def from_env(cls) -> "JEVClient":
        """Use TypeSafe JEV when a key is configured, otherwise use the mock."""
        load_dotenv()
        api_key = os.getenv("JEV_API_KEY", "").strip()
        if api_key:
            from .typesafe import TypeSafeJEVClient

            return TypeSafeJEVClient(api_key=api_key)

        from .mock import MockJEVClient

        return MockJEVClient()

    @abstractmethod
    async def decide(self, request: DecisionRequest) -> DecisionResult:
        """Choose one of the caller-provided options."""
