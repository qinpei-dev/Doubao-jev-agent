from .client import JEVClient
from ..core.models import DecisionRequest, DecisionResult

_RULES: dict[str, tuple[tuple[str, ...], str]] = {
    "paper_skill": (("论文", "paper", "格式", "排版", "学术"), "task requires paper or document formatting"),
    "career_skill": (("招聘", "岗位", "职位", "简历", "求职", "jd"), "task concerns career or job analysis"),
    "coding_skill": (("bug", "代码", "python", "issue", "github", "报错", "编程"), "task requires software development help"),
    "writing_skill": (("小红书", "文案", "写作", "润色", "文章"), "task requires writing or copy generation"),
    "translation_skill": (("翻译", "translate", "英文"), "task requires translation"),
    "coding_agent": (("bug", "代码", "python", "issue", "github", "报错", "编程"), "task requires a coding agent"),
    "writing_agent": (("小红书", "文案", "写作", "润色", "文章"), "task requires a writing agent"),
}


class MockJEVClient(JEVClient):
    async def decide(self, request: DecisionRequest) -> DecisionResult:
        task = request.task.casefold()
        candidates = [
            (sum(1 for term in _RULES[o][0] if term in task), o)
            for o in request.options if o in _RULES
        ]
        score, choice = max(candidates, default=(0, request.options[0]))
        reason = _RULES[choice][1] if score else "no specific rule matched; selected the first available option"
        confidence = (0.94 if choice == "paper_skill" else 0.91) if score else 0.5
        return DecisionResult(decision=choice, confidence=confidence, reason=reason)
