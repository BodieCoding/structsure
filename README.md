# structsure

<p align="center">
  <img src="assets/structsure_logo.png" alt="structsure logo" width="320" />
</p>

A simple, reliable library for getting structured JSON output from LLMs with self-correction.

## Installation

- Ensure you have Python 3.8+
- Install locally in editable mode:

```
pip install -e .
```

Optional backends (recommended via extras):
- Local (Ollama): `pip install -e .[ollama]` and install a model like `ollama pull llama3`
- OpenAI: `pip install -e .[openai]`

## Examples

- Local tasks extraction (no API key): `python examples/local_tasks_demo.py`
- Local resume extraction (no API key): `python examples/resume_extraction_demo.py`
- Hybrid simple usage (auto-detect provider): see `examples/simple_usage.py`

## Quick Example

```python
import os
from pydantic import BaseModel, Field
from structsure import generate

provider = "openai" if os.environ.get("OPENAI_API_KEY") else "ollama"
client = None
if provider == "openai":
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # or OpenAI()

class UserProfile(BaseModel):
    name: str
    age: int
    is_active: bool
    email: str

prompt = "Create a profile for John Doe..."

user_profile = generate(
    client=client,
    model=("gpt-4o" if provider == "openai" else "llama3"),
    response_model=UserProfile,
    prompt=prompt,
    provider=provider,
)
print(user_profile.model_dump_json(indent=2))
```
