from .base import BaseSkill
from .career import CareerSkill
from .paper import PaperSkill
from .coding import CodingSkill
from .research import ResearchSkill
from .writing import WritingSkill


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        if not isinstance(skill, BaseSkill):
            raise TypeError("skill must inherit from BaseSkill")
        if skill.name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def list(self) -> list[BaseSkill]:
        return list(self._skills.values())


def create_default_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for skill in (CareerSkill(), PaperSkill(), CodingSkill(), ResearchSkill(), WritingSkill()):
        registry.register(skill)
    return registry
