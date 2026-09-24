"""TypeSafe response parsing tests using an in-memory HTTP transport."""

import asyncio
import json

import httpx
import pytest

import src.jev.typesafe as typesafe
from src.core.models import DecisionRequest
from src.jev.typesafe import TypeSafeJEVClient


def install_mock_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def async_client_with_mock(*args, **kwargs):
        return real_async_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(typesafe.httpx, "AsyncClient", async_client_with_mock)


def choice_response(choice="coding_skill", confidence=0.8, probabilities=None):
    return {
        "answers": {
            "agent": {
                "type": "choice",
                "choice": choice,
                "confidence": confidence,
                "probabilities": probabilities or {"coding_skill": 0.8, "writing_skill": 0.2},
            }
        }
    }


def test_typesafe_parses_choice_response_with_mock_http(monkeypatch):
    def handle(request):
        assert request.method == "POST"
        assert str(request.url) == TypeSafeJEVClient.endpoint
        assert request.headers["Authorization"] == "Bearer test-only-key"
        payload = json.loads(request.content)
        assert payload["questions"]["agent"]["type"] == "choice"
        assert payload["questions"]["agent"]["criteria"] == {
            "coding_skill": "coding_skill",
            "writing_skill": "writing_skill",
        }
        return httpx.Response(200, json=choice_response())

    install_mock_transport(monkeypatch, handle)
    result = asyncio.run(TypeSafeJEVClient("test-only-key").decide(
        DecisionRequest(task="Fix this Python error", options=["coding_skill", "writing_skill"])
    ))

    assert result.decision == "coding_skill"
    assert result.confidence == 0.8
    assert "next closest option was writing_skill" in result.reason


def test_typesafe_rejects_choice_outside_requested_options(monkeypatch):
    install_mock_transport(monkeypatch, lambda request: httpx.Response(
        200,
        json=choice_response(
            choice="unknown_skill",
            probabilities={"coding_skill": 0.8, "writing_skill": 0.2},
        ),
    ))

    with pytest.raises(ValueError, match="outside the allowed options"):
        asyncio.run(TypeSafeJEVClient("test-only-key").decide(
            DecisionRequest(task="Pick a skill", options=["coding_skill", "writing_skill"])
        ))


def test_typesafe_rejects_choice_inconsistent_with_probabilities(monkeypatch):
    install_mock_transport(monkeypatch, lambda request: httpx.Response(
        200,
        json=choice_response(
            choice="coding_skill",
            probabilities={"coding_skill": 0.2, "writing_skill": 0.8},
        ),
    ))

    with pytest.raises(ValueError, match="inconsistent with its probabilities"):
        asyncio.run(TypeSafeJEVClient("test-only-key").decide(
            DecisionRequest(task="Pick a skill", options=["coding_skill", "writing_skill"])
        ))


def test_typesafe_rejects_malformed_or_mismatched_choice_response(monkeypatch):
    install_mock_transport(monkeypatch, lambda request: httpx.Response(
        200,
        json={"answers": {"agent": {"type": "score", "score": 1.0}}},
    ))

    with pytest.raises(ValueError, match="invalid choice response"):
        asyncio.run(TypeSafeJEVClient("test-only-key").decide(
            DecisionRequest(task="Pick a skill", options=["coding_skill", "writing_skill"])
        ))
