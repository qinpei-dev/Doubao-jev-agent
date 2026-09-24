from ..jev.client import JEVClient
from .models import DecisionRequest, DecisionResult


class DecisionEngine:
    def __init__(self, client: JEVClient):
        self.client = client

    async def decide(self, task: str, options: list[str]) -> DecisionResult:
        request = DecisionRequest(task=task, options=options)
        result = await self.client.decide(request)
        if result.decision not in request.options:
            raise ValueError("JEV returned a decision outside the allowed options")
        return result
