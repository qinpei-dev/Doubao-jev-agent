from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str


BUILTIN_SKILLS = {
    skill.name: skill for skill in (
        Skill("paper_skill", "Paper and document formatting"),
        Skill("career_skill", "Job and career analysis"),
        Skill("coding_skill", "Programming and issue analysis"),
        Skill("writing_skill", "Writing and copy generation"),
    )
}
