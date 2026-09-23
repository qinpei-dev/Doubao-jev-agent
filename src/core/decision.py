from ..jev.client import JEVClient
from .models import DecisionRequest, DecisionResult


class DecisionEngine:
    def __init__(self, client: JEVClient):
        self.client = client

    async def decide(self, task: str, options: list[str]) -> DecisionResult:
        return await self.client.decide(DecisionRequest(task=task, options=options))
