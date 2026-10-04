from typing import get_args

from message_filter.formatting import PROBLEM_LABELS, format_for_whatsapp, format_problems
from message_filter.models import CheckResult, FilteredMessage, Problem


def test_formats_facts_and_questions():
    result = FilteredMessage(
        facts=["Pickup moved to 5:30 Friday"],
        needs_reply=True,
        questions=["Can the inhaler be sent along?"],
        notes=[],
    )

    text = format_for_whatsapp(result)

    assert "- Pickup moved to 5:30 Friday" in text
    assert "NEEDS A REPLY: yes" in text
    assert "- Can the inhaler be sent along?" in text
    assert "NOTES" not in text

def test_formats_empty():
    result = FilteredMessage(
        facts=[],
        needs_reply=False,
        questions=[],
        notes=[],
    )
    
    text = format_for_whatsapp(result)

    assert "NEEDS A REPLY: no" in text
    assert "No practical information" in text


def test_formats_problems_with_labels():
    check = CheckResult(
        problems=[
            Problem(kind="incorrect", description="The pickup time may be wrong."),
            Problem(kind="unflagged", description="The message mentions a lawyer."),
        ]
    )

    text = format_problems(check)

    assert text.startswith("WARNING")
    assert "- May be wrong: The pickup time may be wrong." in text
    assert "- Not flagged: The message mentions a lawyer." in text


def test_every_problem_kind_has_a_label():
    kinds = get_args(Problem.model_fields["kind"].annotation)

    assert set(kinds) == set(PROBLEM_LABELS)