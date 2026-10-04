from message_filter.evaluate import EvalCase, leaked_phrases, load_cases, reply_correct
from message_filter.models import FilteredMessage


def test_cases_file_loads_with_unique_ids():
    cases = load_cases()

    ids = [case.id for case in cases]
    assert len(cases) > 0
    assert len(ids) == len(set(ids))


CASE = EvalCase(
    id="example",
    message="anything",
    expected_facts=[],
    needs_reply=True,
    forbidden=["Typical", "so difficult"],
)


def summary(facts, needs_reply):
    return FilteredMessage(facts=facts, needs_reply=needs_reply, questions=[], notes=[])


def test_reply_correct_compares_with_the_expected_answer():
    assert reply_correct(CASE, summary([], needs_reply=True)) is True
    assert reply_correct(CASE, summary([], needs_reply=False)) is False


def test_leaked_phrases_finds_forbidden_wording():
    result = summary(["Pickup at 5:30. typical of you."], needs_reply=True)

    assert leaked_phrases(CASE, result) == ["Typical"]


def test_leaked_phrases_is_empty_for_a_clean_summary():
    result = summary(["Pickup at 5:30"], needs_reply=True)

    assert leaked_phrases(CASE, result) == []