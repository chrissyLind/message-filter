import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from message_filter.formatting import format_for_whatsapp
from message_filter.llm import SENDER, SONNET, ask
from message_filter.models import FilteredMessage

CASES_FILE = Path("evals/cases.json")
EVAL_DATE = date(2026, 10, 3)


class EvalCase(BaseModel):
    id: str
    message: str
    expected_facts: list[str]
    needs_reply: bool
    expected_flags: list[str] = []
    expected_unclear: list[str] = []
    forbidden: list[str] = []


def load_cases(path: Path = CASES_FILE) -> list[EvalCase]:
    data = json.loads(path.read_text())
    return [EvalCase.model_validate(item) for item in data]


def reply_correct(case: EvalCase, result: FilteredMessage) -> bool:
    return result.needs_reply == case.needs_reply


def leaked_phrases(case: EvalCase, result: FilteredMessage) -> list[str]:
    text = format_for_whatsapp(result).lower()
    return [phrase for phrase in case.forbidden if phrase.lower() in text]


class Verdict(BaseModel):
    reason: str = Field(
        description="One sentence comparing the expected statement with the lines."
    )
    conveyed: bool = Field(
        description="True if the lines convey the expected statement."
    )


JUDGE_PROMPT = f"""You grade summaries of messages between separated parents.

You will receive an expected statement inside <expected> tags and the lines of \
a summary inside <lines> tags. Decide whether the lines convey the expected \
statement.

Rules:
- Compare meaning, not wording.
- Who does what must match. "You" is the parent reading the summary, and \
"{SENDER}" is the other parent.
- Dates, times and places in the expected statement must match. A date written \
in a different format is still a match.
- The lines may contain more than the expected statement. That is fine.
- If there are no lines, the answer is false.
"""


async def judge(expected: str, lines: list[str]) -> Verdict:
    joined = "\n".join(lines)
    content = f"<expected>\n{expected}\n</expected>\n\n<lines>\n{joined}\n</lines>"
    return await ask(SONNET, JUDGE_PROMPT, content, Verdict)