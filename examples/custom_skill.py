"""A standalone custom skill example. Run: python -m examples.custom_skill"""

from src.skills import BaseSkill, SkillExecutor, SkillRegistry


class CustomSkill(BaseSkill):
    name = "custom_skill"
    description = "Demonstrate a developer-defined local skill."

    def execute(self, input: str) -> dict:
        return {
            "skill": self.name,
            "status": "completed",
            "result": f"Custom skill received: {input}",
        }


def main() -> None:
    registry = SkillRegistry()
    registry.register(CustomSkill())
    result = SkillExecutor(registry).execute("custom_skill", "Hello from Doubao")
    print(result)


if __name__ == "__main__":
    main()
