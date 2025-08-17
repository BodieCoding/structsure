"""
Local-only demo: Extract a structured task list from free-form text using a local Ollama model.

Prerequisites:
- Install and run Ollama: https://ollama.com
- Install a local model (e.g., llama3): `ollama pull llama3`
- Install Python deps: `pip install -e .[ollama]`

Then run:
    python examples/local_tasks_demo.py
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from structsure import generate, MaxRetriesExceededError


class Task(BaseModel):
    title: str = Field(description="Short description of the task")
    due_date: Optional[str] = Field(default=None, description="Due date in natural language or ISO format, if mentioned")
    priority: Literal["low", "medium", "high"] = Field(description="Priority level if inferable")
    completed: bool = Field(default=False, description="Whether the task is already done")
    tags: List[str] = Field(default_factory=list, description="Any relevant tags (e.g., project, context)")


class TaskList(BaseModel):
    tasks: List[Task]


sample_text = (
    "Team notes: Follow up with Alice about the Q3 report by Friday. "
    "Schedule dentist appointment for next month. "
    "Buy milk and eggs. "
    "Finish the API spec review (high priority) before Wednesday. "
    "Optional: consider upgrading the staging database next sprint."
)


def main() -> None:
    try:
        print("Using local Ollama (no API key required)...")
        result = generate(
            client=None,  # use module-level ollama client
            model="llama3",  # ensure you've pulled this model: `ollama pull llama3`
            response_model=TaskList,
            prompt=(
                "Extract a structured list of actionable tasks from the following text. "
                "Infer reasonable priorities (low/medium/high), set completed to false unless clearly done, "
                "and include any tags you find. Only return the JSON object.\n\n" + sample_text
            ),
            max_retries=3,
            provider="ollama",  # force local backend
        )
        print("\nStructured tasks:\n")
        print(result.model_dump_json(indent=2))
    except MaxRetriesExceededError:
        print("\nFailed to produce valid structured tasks after multiple attempts.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
