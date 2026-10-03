from message_filter.formatting import format_for_whatsapp
from message_filter.models import FilteredMessage


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
