import json
from datetime import date
from pathlib import Path
import asyncio
import sys

from pydantic import BaseModel, Field

from message_filter.formatting import format_for_whatsapp
from message_filter.llm import SENDER, SONNET, ask
from message_filter.models import FilteredMessage
from message_filter.filter import filter_message
from message_filter.llm import HAIKU, SENDER, SONNET, ask
from message_filter.check import check_summary

CASES_FILE = Path("evals/cases.json")
EVAL_DATE = date(2026, 10, 3)
MODELS = {"haiku": HAIKU, "sonnet": SONNET}


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
- Judge the practical content. Framing does not have to match: "your ex says \
X should happen" and "X needs to happen" convey the same thing.
"""


async def judge(expected: str, lines: list[str]) -> Verdict:
    joined = "\n".join(lines)
    content = f"<expected>\n{expected}\n</expected>\n\n<lines>\n{joined}\n</lines>"
    return await ask(SONNET, JUDGE_PROMPT, content, Verdict)


class CaseScore(BaseModel):
    id: str
    facts_expected: int
    flags_expected: int
    unclear_expected: int
    missed_facts: list[str]
    missed_flags: list[str]
    missed_unclear: list[str]
    reply_correct: bool
    leaked: list[str]
    checker_problems: list[str]


async def missed(expected: list[str], lines: list[str]) -> list[str]:
    misses = []
    for item in expected:
        verdict = await judge(item, lines)
        if not verdict.conveyed:
            misses.append(f"{item} -- {verdict.reason}")
    return misses


async def evaluate_case(case: EvalCase, model: str) -> CaseScore:
    result = await filter_message(case.message, today=EVAL_DATE, model=model)
    check = await check_summary(case.message, result, today=EVAL_DATE)
    return CaseScore(
        id=case.id,
        facts_expected=len(case.expected_facts),
        flags_expected=len(case.expected_flags),
        unclear_expected=len(case.expected_unclear),
        missed_facts=await missed(case.expected_facts, result.facts + result.questions),
        missed_flags=await missed(case.expected_flags, result.notes),
        missed_unclear=await missed(case.expected_unclear, result.notes),
        reply_correct=reply_correct(case, result),
        leaked=leaked_phrases(case, result),
        checker_problems=[
            f"{problem.kind}: {problem.description}" for problem in check.problems
        ],
    )


def rate(caught: int, expected: int) -> str:
    if expected == 0:
        return "n/a"
    return f"{caught}/{expected} ({caught / expected:.0%})"


def print_report(scores: list[CaseScore]) -> None:
    filter_errors = 0
    caught = 0
    filter_correct = 0
    false_alarms = 0

    for score in scores:
        problems = (
            [f"missed fact: {item}" for item in score.missed_facts]
            + [f"missed flag: {item}" for item in score.missed_flags]
            + [f"missed unclear: {item}" for item in score.missed_unclear]
            + [f"hostile wording got through: {phrase}" for phrase in score.leaked]
        )
        if not score.reply_correct:
            problems.append("needs-a-reply is wrong")

        print(f"{'FAIL' if problems else 'PASS'}  {score.id}")
        for problem in problems:
            print(f"      {problem}")

        if problems:
            filter_errors += 1
            if score.checker_problems:
                caught += 1
                label = "checker caught"
            else:
                print("      CHECKER MISSED IT: it reported no problems")
        else:
            filter_correct += 1
            if score.checker_problems:
                false_alarms += 1
                label = "CHECKER FALSE ALARM"
        for item in score.checker_problems:
            print(f"      {label} -> {item}")

    facts = sum(score.facts_expected for score in scores)
    flags = sum(score.flags_expected for score in scores)
    unclear = sum(score.unclear_expected for score in scores)
    missed_facts = sum(len(score.missed_facts) for score in scores)
    missed_flags = sum(len(score.missed_flags) for score in scores)
    missed_unclear = sum(len(score.missed_unclear) for score in scores)
    replies = sum(score.reply_correct for score in scores)
    clean = sum(not score.leaked for score in scores)

    print()
    print(f"Facts caught:            {rate(facts - missed_facts, facts)}")
    print(f"Flags caught:            {rate(flags - missed_flags, flags)}")
    print(f"Unclear details noted:   {rate(unclear - missed_unclear, unclear)}")
    print(f"Needs-a-reply correct:   {rate(replies, len(scores))}")
    print(f"Free of hostile wording: {rate(clean, len(scores))}")
    print()
    print(f"Checker caught filter errors: {rate(caught, filter_errors)}")
    print(f"Checker false alarms:         {rate(false_alarms, filter_correct)}")
    

async def main(model_name: str) -> None:
    model = MODELS[model_name]
    print(f"Filter model: {model_name}")
    scores = []
    for case in load_cases():
        print(f"Running {case.id}...")
        scores.append(await evaluate_case(case, model))
    print()
    print_report(scores)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "sonnet"))