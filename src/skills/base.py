from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """Interface implemented by every executable skill."""

    name: str
    description: str

    @abstractmethod
    def execute(self, input: str) -> dict:
        """Execute this skill for the supplied user input."""
