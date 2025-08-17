import os
import json
from typing import Type, TypeVar, Any, Literal, List, Dict, Optional
from pydantic import BaseModel, ValidationError

from .exceptions import MaxRetriesExceededError

# Define a generic type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


def generate(
    client: Any,
    model: str,
    response_model: Type[T],
    prompt: str,
    max_retries: int = 3,
    provider: Optional[Literal["openai", "ollama"]] = None,
) -> T:
    """
    Generates a structured response from an LLM, validated against a Pydantic model.

    Args:
        client: An initialized client instance. For provider="openai", pass openai.OpenAI() or None.
                For provider="ollama", pass an ollama client (ollama.Client()) or None to use module-level API.
        model: The name of the LLM model to use (e.g., "gpt-4o" or "llama3").
        response_model: The Pydantic model to validate the response against.
        prompt: The user's prompt.
        max_retries: The maximum number of times to retry if validation fails.
        provider: Which backend to use: "openai" or "ollama". If None, uses "openai" when OPENAI_API_KEY is set, otherwise "ollama".

    Returns:
        An instance of the Pydantic model.

    Raises:
        MaxRetriesExceededError: If the model fails to produce a valid response after all retries.
    """
    # Auto-detect provider when not specified
    resolved_provider: str = provider or ("openai" if os.environ.get("OPENAI_API_KEY") else "ollama")

    schema_json = json.dumps(response_model.model_json_schema(), indent=2)
    system_prompt = f"""
You are an expert at generating structured JSON data. The user will provide a prompt, and you must respond with a JSON object that strictly adheres to the following JSON Schema.
Do NOT output anything other than the single JSON object. Do not add any commentary, markdown, or any other text.

JSON Schema:
{schema_json}
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    def _call_model(msgs: List[Dict[str, str]]) -> str:
        if resolved_provider == "openai":
            # Use provided client if available, else construct one (env var should be present)
            if client is None:
                try:
                    from openai import OpenAI  # type: ignore
                    oa_client = OpenAI()  # relies on OPENAI_API_KEY in env
                except ImportError as ie:
                    raise RuntimeError("openai package is not installed. Please `pip install openai`.") from ie
            else:
                oa_client = client
            response = oa_client.chat.completions.create(
                model=model,
                messages=msgs,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        elif resolved_provider == "ollama":
            # Use provided client if it has chat; otherwise import module-level API
            try:
                if client is not None and hasattr(client, "chat"):
                    resp = client.chat(model=model, messages=msgs, format="json")
                else:
                    import ollama  # type: ignore
                    resp = ollama.chat(model=model, messages=msgs, format="json")
            except ImportError as ie:
                raise RuntimeError("Ollama Python package is not installed. Please `pip install ollama`.") from ie
            # Ollama returns a dict
            return resp["message"]["content"]
        else:
            raise ValueError(f"Unsupported provider: {resolved_provider}")

    for attempt in range(max_retries):
        try:
            content = _call_model(messages)
            # Validate the JSON output against the Pydantic model
            parsed_obj = response_model.model_validate_json(content)
            return parsed_obj
        except (ValidationError, json.JSONDecodeError) as e:
            # If validation fails, create a new message asking the model to fix its mistake
            error_message = (
                "Your last attempt failed validation with the following error:\n"
                f"{e}\n"
                "Please correct your output and try again. Ensure your response is ONLY the corrected JSON object."
            )
            messages.append({"role": "assistant", "content": content})  # Add the failed attempt
            messages.append({"role": "user", "content": error_message})  # Add the correction prompt
            print(f"Attempt {attempt + 1} failed. Retrying...")  # Optional: for debugging

    raise MaxRetriesExceededError()
