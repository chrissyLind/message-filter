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

class ReplyOption(BaseModel):
    label: str = Field(
        description="A short label for this option, such as 'Agree', 'Decline' or 'Acknowledge'."
    )
    text: str = Field(
        description="The reply text, ready to send. Three sentences at most."
    )


class ReplyDrafts(BaseModel):
    options: list[ReplyOption] = Field(
        description="One to three alternative replies for the recipient to choose from."
    )