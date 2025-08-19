from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import os

from structsure.core import generate
from structsure.server.models import SchemaRecord, RunRecord
from structsure.schema import model_from_spec
from structsure.server import db as dbmod
from structsure.pro import license_plan, pro_enabled, get_license_info

app = FastAPI(title="Structsure API")

# Static for assets (logo)
assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "assets")
app.mount("/assets", StaticFiles(directory=os.path.abspath(assets_dir)), name="assets")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
# Expose licensing helpers to templates
try:
    templates.env.globals["license_plan"] = license_plan
    templates.env.globals["pro_enabled"] = pro_enabled
    templates.env.globals["license_info"] = get_license_info
except Exception:
    pass

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

    # Enforce CE gating: if not Pro, force local-only provider
    if not pro_enabled():
        provider_val = "ollama"

    default_model = req.model or ("gpt-4o" if provider_val == "openai" else "llama3")

    result = generate(
        client=None,
        model=default_model,
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
            model=req.model or default_model,
        )
        return RunRecord(**rec)

    global _next_run_id
    run = RunRecord(
        id=_next_run_id,
        schema_id=stored.id or req.schema_id,
        prompt=req.prompt,
        output_json=result.model_dump_json(),
        provider=provider_val,
        model=req.model or default_model,
    )
    RUNS[_next_run_id] = run
    _next_run_id += 1
    return run

@app.get("/ui", response_class=HTMLResponse)
def ui_index(request: Request):
    # list recent schemas
    if DSN:
        # naive listing via direct SQL
        recs = []
        # use db connection to fetch top 20
        try:
            from sqlalchemy import text  # type: ignore
            with dbmod.db_conn(DSN) as eng:
                with eng.begin() as conn:  # type: ignore[attr-defined]
                    rows = conn.execute(text("SELECT id, name, description, schema_json, updated_at FROM schemas ORDER BY updated_at DESC LIMIT 20")).mappings().all()
                    recs = [SchemaRecord(**dict(r)) for r in rows]
        except Exception:
            recs = []
    else:
        recs = list(SCHEMAS.values())
    return templates.TemplateResponse("index.html", {"request": request, "schemas": recs})

@app.post("/ui/schemas")
def ui_create_schema(name: str = "", description: str = "", schema_json: str = ""):
    schema = SchemaRecord(name=name, description=description or None, schema_json=schema_json)
    created = create_schema(schema)
    return RedirectResponse(url=f"/ui/schemas/{created.id}", status_code=303)

@app.get("/ui/schemas/{schema_id}", response_class=HTMLResponse)
def ui_get_schema(request: Request, schema_id: int):
    schema = get_schema(schema_id)
    # recent runs (memory only to keep simple; in DSN mode, fetch last 10)
    runs = []
    if DSN:
        try:
            from sqlalchemy import text  # type: ignore
            with dbmod.db_conn(DSN) as eng:
                with eng.begin() as conn:  # type: ignore[attr-defined]
                    rows = conn.execute(text("SELECT id, schema_id, prompt, output_json, provider, model, created_at FROM runs WHERE schema_id=:sid ORDER BY id DESC LIMIT 10"), {"sid": schema_id}).mappings().all()
                    runs = [RunRecord(**dict(r)) for r in rows]
        except Exception:
            runs = []
    else:
        runs = [r for r in RUNS.values() if r.schema_id == schema_id]
    return templates.TemplateResponse("schema.html", {"request": request, "schema": schema, "runs": runs})

@app.post("/ui/generate")
def ui_generate(schema_id: int, instructions: str = "", example_json: str = "", source_text: str = ""):
    parts = []
    if instructions.strip():
        parts.append(instructions.strip())
    if example_json.strip():
        parts.append("Example JSON:\n" + example_json.strip())
    if source_text.strip():
        parts.append("Input:\n" + source_text.strip())
    prompt = "\n\n".join(parts).strip()

    _ = generate_run(GenerateRequest(schema_id=schema_id, prompt=prompt))
    return RedirectResponse(url=f"/ui/schemas/{schema_id}", status_code=303)
