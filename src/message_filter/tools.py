from datetime import date, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def next_weekday(weekday: str, today: date) -> date:
    target = WEEKDAYS.index(weekday.lower())
    days_ahead = (target - today.weekday() - 1) % 7 + 1
    return today + timedelta(days=days_ahead)


NEXT_WEEKDAY_TOOL = {
    "name": "next_weekday",
    "description": (
        "Get the calendar date of the next given weekday, counting from tomorrow. "
        "Use this whenever a message mentions a weekday such as 'Friday', "
        "instead of working out the date yourself."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "weekday": {
                "type": "string",
                "enum": WEEKDAYS,
                "description": "The weekday to find.",
            }
        },
        "required": ["weekday"],
    },
}

TOOLS = [NEXT_WEEKDAY_TOOL]


def run_tool(name: str, tool_input: dict, today: date) -> str:
    if name == "next_weekday":
        result = next_weekday(tool_input["weekday"], today)
        return result.strftime("%A, %B %d, %Y")
    raise ValueError(f"Unknown tool: {name}")