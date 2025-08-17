import json
import os
from typing import Optional, Dict, Any, Type, Literal, cast

from pydantic import BaseModel, create_model

from .core import generate


# Minimal MCP server using the `mcp` package's simple server helpers.
# Exposes one tool: structsure.generate
try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore


def _model_from_schema(schema: Dict[str, Any]) -> Type[BaseModel]:
    title = schema.get("title", "StructsureModel")
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields = {}
    for name, spec in properties.items():
        typ = spec.get("type", "string")
        py_type: object = str
        if typ == "integer":
            py_type = int
        elif typ == "number":
            py_type = float
        elif typ == "boolean":
            py_type = bool
        elif typ == "array":
            py_type = list
        elif typ == "object":
            py_type = dict
        default = ... if name in required else None
        fields[name] = (py_type, default)

    return create_model(title, **fields)  # type: ignore[arg-type]


def main() -> None:
    if FastMCP is None:
        raise RuntimeError("mcp package not installed. Install with `pip install -e .[mcp]`.")

    mcp = FastMCP("structsure")

    @mcp.tool()
    def generate_structured(
        prompt: str,
        schema_json: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Generate a structured JSON response matching the provided (optional) JSON Schema.
        If no schema is provided, a minimal model with a single `content` field is used.
        """
        if schema_json:
            ResponseModel: Type[BaseModel] = _model_from_schema(json.loads(schema_json))  # type: ignore[assignment]
        else:
            class ResponseModel(BaseModel):
                content: str

        resolved_provider: Literal["openai", "ollama"] = (
            "openai" if os.environ.get("OPENAI_API_KEY") else "ollama"
        ) if provider is None else cast(Literal["openai", "ollama"], provider)
        resolved_model = model or ("gpt-4o" if resolved_provider == "openai" else "llama3")

        obj = generate(
            client=None,
            model=resolved_model,
            response_model=ResponseModel,
            prompt=prompt,
            max_retries=max_retries,
            provider=resolved_provider,
        )
        return obj.model_dump_json(indent=2)

    mcp.run()


if __name__ == "__main__":
    main()
