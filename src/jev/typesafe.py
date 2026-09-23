"""Client for TypeSafe's hosted System One / Jev API."""

import httpx

from ..core.models import DecisionRequest, DecisionResult
from .client import JEVClient


class TypeSafeJEVClient(JEVClient):
    """Send constrained choice decisions to TypeSafe's Jev model."""

    endpoint = "https://api.typesafe.ai/v1/systemone"
    model = "jev-latest"

    def __init__(self, api_key: str):
        if not api_key.strip():
            raise ValueError("JEV_API_KEY must not be empty")
        self.api_key = api_key.strip()

    async def decide(self, request: DecisionRequest) -> DecisionResult:
        payload = {
            "state": request.task,
            "model": self.model,
            "questions": {
                "agent": {
                    "type": "choice",
                    "instructions": "Choose the agent best suited to handle the user's task.",
                    "criteria": {option: option for option in request.options},
                }
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            body = response.json()

        try:
            answer = body["answers"]["agent"]
            decision = answer["choice"]
            confidence = answer["confidence"]
            probabilities = answer.get("probabilities", {})
        except (KeyError, TypeError) as exc:
            raise ValueError("TypeSafe JEV returned an invalid choice response") from exc

        if decision not in request.options:
            raise ValueError("TypeSafe JEV returned a decision outside the allowed options")

        # The API returns a typed choice and probabilities, but no free-text reason.
        confidence_text = f"{confidence:.0%}" if isinstance(confidence, (int, float)) else str(confidence)
        reason = f"TypeSafe JEV selected {decision} with {confidence_text} confidence."
        if probabilities:
            ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
            if len(ranked) > 1:
                reason += f" The next closest option was {ranked[1][0]}."

        return DecisionResult(decision=decision, confidence=confidence, reason=reason)
