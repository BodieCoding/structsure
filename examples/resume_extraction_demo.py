"""
Local-only demo: Extract a structured resume from free-form text using a local Ollama model.

Prerequisites:
- Install and run Ollama: https://ollama.com
- Install a local model (e.g., llama3): `ollama pull llama3`
- Install Python deps: `pip install -e .[ollama]`

Then run:
    python examples/resume_extraction_demo.py
"""
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from structsure import generate, MaxRetriesExceededError


class ExperienceItem(BaseModel):
    company: str = Field(description="Company name")
    role: str = Field(description="Job title/role")
    start_date: Optional[str] = Field(default=None, description="Start date (natural language or YYYY-MM)")
    end_date: Optional[str] = Field(default=None, description="End date or 'Present'")
    highlights: List[str] = Field(default_factory=list, description="Key accomplishments or responsibilities")


class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class Resume(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)


sample_resume_text = (
    "Jane Doe is a software engineer based in Austin, TX. Email: jane.doe@example.com. "
    "LinkedIn: linkedin.com/in/janedoe, GitHub: github.com/janedoe. "
    "Summary: Full-stack engineer with 7+ years of experience building scalable web apps. "
    "Skills: Python, FastAPI, React, Postgres, Docker, AWS. "
    "Experience: At Acme Corp (Senior Software Engineer, 2022-Present), led migration to FastAPI, "
    "cut API latency by 40%, mentored 4 engineers. At Beta Labs (Software Engineer, 2019-2022), "
    "built internal tooling in Python and React; launched CI/CD with GitHub Actions. "
    "Education: B.S. in Computer Science from UT Austin, 2015-2019."
)

# Preprompt/instructions and an example JSON to guide the model
pre_instructions = (
    "Extract a structured resume JSON matching the Pydantic schema. "
    "Only return the JSON object with no extra commentary."
)

example_json = {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "555-123-4567",
    "location": "Austin, TX",
    "links": [
        "https://linkedin.com/in/janedoe",
        "https://github.com/janedoe"
    ],
    "summary": "Full-stack engineer with experience in Python and React.",
    "skills": ["Python", "FastAPI", "React", "Postgres", "Docker", "AWS"],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Senior Software Engineer",
            "start_date": "2022-01",
            "end_date": "Present",
            "highlights": [
                "Led migration to FastAPI",
                "Reduced API latency by 40%",
                "Mentored 4 engineers"
            ]
        }
    ],
    "education": [
        {
            "institution": "UT Austin",
            "degree": "B.S. in Computer Science",
            "start_year": 2015,
            "end_year": 2019
        }
    ]
}
example_json_str = json.dumps(example_json, indent=2)


def main() -> None:
    try:
        print("Using local Ollama (no API key required)...")
        result = generate(
            client=None,
            model="llama3",
            response_model=Resume,
            prompt="\n\n".join([
                pre_instructions,
                "Example JSON:\n" + example_json_str,
                "Input:\n" + sample_resume_text,
            ]),
            max_retries=3,
            provider="ollama",
        )
        print("\nStructured resume:\n")
        print(result.model_dump_json(indent=2))
    except MaxRetriesExceededError:
        print("\nFailed to produce a valid structured resume after multiple attempts.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
