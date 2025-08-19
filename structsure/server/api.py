from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os

from structsure.core import generate
from structsure.server.models import SchemaRecord, RunRecord
from structsure.schema import model_from_spec
from structsure.server import db as dbmod

app = FastAPI(title="Structsure API")

DSN = os.environ.get("STRUCTSURE_DSN")  # e.g., postgresql+psycopg://user:pass@host/db
if DSN:
    try:
        dbmod.init_db(DSN)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to init DB: {e}")

# In-memory store (used when DSN is not set)
SCHEMAS: dict[int, SchemaRecord] = {}
RUNS: dict[int, RunRecord] = {}
_next_schema_id = 1
_next_run_id = 1

class GenerateRequest(BaseModel):
    schema_id: int
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None
    max_retries: int = 3

@app.post("/schemas", response_model=SchemaRecord)
def create_schema(schema: SchemaRecord) -> SchemaRecord:
    if DSN:
        rec = dbmod.create_schema(DSN, schema.name, schema.description, schema.schema_json)
        return SchemaRecord(**rec)
    global _next_schema_id
    if schema.id is None:
        schema.id = _next_schema_id
    SCHEMAS[schema.id] = schema
    _next_schema_id += 1
    return schema

@app.get("/schemas/{schema_id}", response_model=SchemaRecord)
def get_schema(schema_id: int) -> SchemaRecord:
    if DSN:
        rec = dbmod.get_schema_by_id(DSN, schema_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Schema not found")
        return SchemaRecord(**rec)
    if schema_id not in SCHEMAS:
        raise HTTPException(status_code=404, detail="Schema not found")
    return SCHEMAS[schema_id]

@app.post("/generate", response_model=RunRecord)
def generate_run(req: GenerateRequest) -> RunRecord:
    # Load schema
    stored = get_schema(req.schema_id)

    try:
        spec = json.loads(stored.schema_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid stored schema_json: {e}")

    SchemaModel = model_from_spec(spec)

    # normalize provider to expected literal
    provider_val: Optional[str] = req.provider if req.provider in {"openai", "ollama"} else None

    result = generate(
        client=None,
        model=req.model or ("gpt-4o" if provider_val == "openai" else "llama3"),
        response_model=SchemaModel,
        prompt=req.prompt,
        provider=provider_val,  # type: ignore[arg-type]
        max_retries=req.max_retries,
    )

    if DSN:
        rec = dbmod.create_run(
            DSN,
            schema_id=stored.id or 0,
            prompt=req.prompt,
            output_json=result.model_dump_json(),
            provider=provider_val,
            model=req.model,
        )
        return RunRecord(**rec)

    global _next_run_id
    run = RunRecord(
        id=_next_run_id,
        schema_id=stored.id or req.schema_id,
        prompt=req.prompt,
        output_json=result.model_dump_json(),
        provider=provider_val,
        model=req.model,
    )
    RUNS[_next_run_id] = run
    _next_run_id += 1
    return run
