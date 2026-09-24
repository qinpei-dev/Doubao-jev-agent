"""Client for TypeSafe's hosted System One / Jev API."""

from typing import Literal

import httpx
from pydantic import BaseModel, Field, field_validator

from ..core.models import DecisionRequest, DecisionResult
from .client import JEVClient


class _ChoiceAnswer(BaseModel):
    type: Literal["choice"]
    choice: str
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]

    @field_validator("probabilities")
    @classmethod
    def probabilities_must_be_valid(cls, value: dict[str, float]) -> dict[str, float]:
        if not value or any(not 0 <= probability <= 1 for probability in value.values()):
            raise ValueError("probabilities must contain values between 0 and 1")
        return value


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
                    "instructions": "Choose the option that best fits the task and caller-provided criteria.",
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

        try:
            body = response.json()
            answer = _ChoiceAnswer.model_validate(body["answers"]["agent"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("TypeSafe JEV returned an invalid choice response") from exc

        if answer.choice not in request.options:
            raise ValueError("TypeSafe JEV returned a decision outside the allowed options")
        if set(answer.probabilities) != set(request.options):
            raise ValueError("TypeSafe JEV returned probabilities outside the requested options")
        if answer.probabilities[answer.choice] < max(answer.probabilities.values()):
            raise ValueError("TypeSafe JEV returned a choice inconsistent with its probabilities")

        # The API returns a typed choice and probabilities, but no free-text reason.
        reason = f"TypeSafe JEV selected {answer.choice} with {answer.confidence:.0%} confidence."
        alternatives = sorted(
            ((option, probability) for option, probability in answer.probabilities.items() if option != answer.choice),
            key=lambda item: item[1],
            reverse=True,
        )
        if alternatives:
            reason += f" The next closest option was {alternatives[0][0]}."

        return DecisionResult(decision=answer.choice, confidence=answer.confidence, reason=reason)
