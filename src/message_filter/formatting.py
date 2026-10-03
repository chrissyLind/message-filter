from message_filter.models import FilteredMessage


def format_for_whatsapp(result: FilteredMessage) -> str:
    lines = []

    if result.facts:
        lines.append("FACTS:")
        for fact in result.facts:
            lines.append(f"- {fact}")
    else:
        lines.append("No practical information in this message.")

    lines.append("")
    lines.append(f"NEEDS A REPLY: {'yes' if result.needs_reply else 'no'}")
    for question in result.questions:
        lines.append(f"- {question}")

    if result.notes:
        lines.append("")
        lines.append("NOTES:")
        for note in result.notes:
            lines.append(f"- {note}")

    return "\n".join(lines)