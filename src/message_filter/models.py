from pydantic import BaseModel, Field


class FilteredMessage(BaseModel):
    facts: list[str] = Field(
        description="Practical facts, one per item, restated neutrally. Empty if there are none."
    )
    needs_reply: bool = Field(
        description="True if the message contains a question or request that needs an answer."
    )
    questions: list[str] = Field(
        description="The questions or requests that need an answer, restated neutrally. Empty if none."
    )
    notes: list[str] = Field(
        description="Anything unclear, and anything flagged such as threats, safety concerns "
        "or legal action. Empty if none."
    )