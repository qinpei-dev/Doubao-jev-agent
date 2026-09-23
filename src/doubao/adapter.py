from typing import Any
from .skill import BUILTIN_SKILLS


class DoubaoAdapter:
    """Provider-neutral boundary; intentionally does not call a Doubao API."""
    async def send_message(self, message: str) -> dict[str, Any]:
        return {"message": message, "status": "adapter_stub"}

    async def execute_skill(self, skill_name: str, task: str) -> dict[str, Any]:
        if skill_name not in BUILTIN_SKILLS:
            raise ValueError(f"Unknown skill: {skill_name}")
        return {"skill": skill_name, "task": task, "status": "adapter_stub"}
