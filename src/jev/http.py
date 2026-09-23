import httpx
from .client import JEVClient
from ..core.models import DecisionRequest, DecisionResult


class HTTPJEVClient(JEVClient):
    """Generic async JEV HTTP adapter. Expects {decision, confidence, reason}."""
    def __init__(self, endpoint: str, api_key: str):
        if not endpoint or not api_key:
            raise ValueError("JEV_API_URL and JEV_API_KEY are required in real mode")
        self.endpoint = endpoint
        self.api_key = api_key

    async def decide(self, request: DecisionRequest) -> DecisionResult:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                self.endpoint,
                json=request.model_dump(),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            result = DecisionResult.model_validate(response.json())
        if result.decision not in request.options:
            raise ValueError("JEV returned a decision outside the allowed options")
        return result
