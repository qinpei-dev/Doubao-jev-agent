from ..core.models import DecisionResult
from .registry import SkillRegistry


class SkillExecutor:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def execute(self, decision: DecisionResult | str, input: str) -> dict:
        skill_name = decision.decision if isinstance(decision, DecisionResult) else decision
        skill = self.registry.get(skill_name)
        if skill is None:
            raise ValueError(f"No skill registered for decision: {skill_name}")
        return skill.execute(input)
