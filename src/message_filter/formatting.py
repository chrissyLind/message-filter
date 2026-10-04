from message_filter.models import CheckResult, FilteredMessage, ReplyDrafts


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

def format_drafts_note(drafts: ReplyDrafts) -> str:
    labels = ", ".join(option.label for option in drafts.options)
    return f"DRAFT REPLIES ({labels}) follow as separate messages. Copy the one you want to send."


PROBLEM_LABELS = {
    "unflagged": "Not flagged",
    "incorrect": "May be wrong",
    "missing": "May be missing",
    "hostile": "Hostile wording",
}


def format_problems(check: CheckResult) -> str:
    lines = ["WARNING: this summary may have problems. Check the original message."]
    for problem in check.problems:
        lines.append(f"- {PROBLEM_LABELS[problem.kind]}: {problem.description}")
    return "\n".join(lines)