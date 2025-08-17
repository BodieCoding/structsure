import json
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, create_model

# Minimal helpers to build/infer JSON Schema and Pydantic models


_BASIC_TYPE_MAP: Dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def model_from_spec(spec: Dict[str, Any], title: str = "StructsureModel") -> Type[BaseModel]:
    """
    Build a Pydantic model from a simple spec of the form:
      {
        "properties": {
          "name": {"type": "string", "description": "...", "required": true},
          "age": {"type": "integer"}
        }
      }
    Only basic JSON types are supported. Arrays/objects are not deeply typed in this minimal helper.
    """
    props: Dict[str, Any] = spec.get("properties", {})
    fields: Dict[str, Tuple[type, Any]] = {}
    required_fields = [k for k, v in props.items() if v.get("required")]

    for name, cfg in props.items():
        t = cfg.get("type", "string")
        py_t = _BASIC_TYPE_MAP.get(t, str)
        default = ... if name in required_fields else None
        fields[name] = (py_t, default)

    return create_model(title, **fields)  # type: ignore[arg-type]


def json_schema_from_spec(spec: Dict[str, Any], title: str = "StructsureModel") -> Dict[str, Any]:
    """
    Produce a JSON Schema from the same simple spec. Uses Pydantic to emit the schema.
    """
    Model = model_from_spec(spec, title)
    return Model.model_json_schema()


def infer_json_schema_from_examples(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Infer a JSON Schema from example JSON objects using genson if available.
    Fallback: merge keys and set type to 'string'.
    """
    try:
        from genson import SchemaBuilder  # type: ignore
    except Exception:
        # very naive fallback
        keys = set()
        for s in samples:
            keys.update(s.keys())
        spec = {
            "properties": {k: {"type": "string"} for k in sorted(keys)},
        }
        return json_schema_from_spec(spec)

    builder = SchemaBuilder()
    builder.add_schema({"type": "object", "properties": {}})
    for s in samples:
        builder.add_object(s)
    return builder.to_schema()


def load_examples(path: str) -> List[Dict[str, Any]]:
    """
    Load examples from a .json (list or single object) or .jsonl file.
    """
    if path.lower().endswith(".jsonl"):
        out: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                out.append(json.loads(line))
        return out
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError("Unsupported JSON examples format; expected object, list, or JSONL")
