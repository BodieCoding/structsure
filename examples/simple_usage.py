import os
from pydantic import BaseModel, Field
from structsure import generate, MaxRetriesExceededError

# --- Backend selection ---
# If OPENAI_API_KEY is set, use OpenAI. Otherwise, try local Ollama.
provider = "openai" if os.environ.get("OPENAI_API_KEY") else "ollama"
client = None

if provider == "openai":
    from openai import OpenAI  # type: ignore
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # raises if missing
else:
    try:
        import ollama  # type: ignore
        # client = ollama.Client()  # optional; module-level is fine
        client = None  # generate() will use module-level ollama.chat
    except ImportError:
        print("Error: ollama Python package not installed. Run `pip install ollama`.")
        raise


# --- Define the desired data structure ---
class UserProfile(BaseModel):
    name: str = Field(description="The full name of the user.")
    age: int = Field(description="The age of the user.")
    is_active: bool = Field(description="Indicates if the user's account is active.")
    email: str = Field(description="The primary email address of the user.")


# --- Create a prompt ---
user_text = (
    "Create a profile for John Doe. He is 30 years old, his email is john.d@example.com, "
    "and his account is currently enabled."
)

# --- Generate the structured data ---
try:
    print(f"Generating user profile using {provider}...")
    user_profile = generate(
        client=client,
        model=("gpt-4o" if provider == "openai" else "llama3"),
        response_model=UserProfile,
        prompt=user_text,
        provider=provider,
    )
    print("\nSuccessfully generated profile:")
    print(user_profile.model_dump_json(indent=2))

except MaxRetriesExceededError:
    print("\nFailed to generate user profile after multiple attempts.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
