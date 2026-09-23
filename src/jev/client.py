from abc import ABC, abstractmethod
from ..core.models import DecisionRequest, DecisionResult


class JEVClient(ABC):
    @abstractmethod
    async def decide(self, request: DecisionRequest) -> DecisionResult:
        """Choose one of the caller-provided options."""
