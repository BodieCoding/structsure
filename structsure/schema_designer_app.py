"""
Streamlit Schema Designer: Define a simple spec for fields and generate JSON Schema + test a prompt locally.
Run:
  streamlit run structsure/schema_designer_app.py
Requirements:
  pip install -e .[streamlit,ollama]
"""
import json
from typing import Dict, Any
import streamlit as st
from pathlib import Path

from structsure.schema import model_from_spec
from structsure.core import generate
from structsure.pro import pro_enabled

# Resolve logo path relative to project root
_project_root = Path(__file__).resolve().parent.parent
_logo_path = _project_root / "assets" / "structsure_logo.png"
_page_icon = str(_logo_path)

st.set_page_config(page_title="Structsure Schema Designer", page_icon=_page_icon, layout="wide")

# Sidebar logo
with st.sidebar:
    if _logo_path.exists():
        st.image(_page_icon, use_container_width =True)

st.title("Schema Designer for AI Output")
st.caption("Design schemas, prompt models, and get valid JSON with self-correction — locally or in the cloud.")

with st.sidebar:
    st.markdown("### Backend")
    is_pro = pro_enabled()
    provider_options = ["ollama"] + (["openai"] if is_pro else [])
    provider = st.selectbox("Provider", options=provider_options, index=0)
    if not is_pro:
        st.caption("Cloud providers are available in Pro. Activate a license via LICENZY_LICENSE_KEY or 'licenzy activate'.")
    model = st.text_input("Model", value="llama3" if provider == "ollama" else "gpt-4o")
    retries = st.number_input("Max retries", min_value=1, max_value=10, value=3)
    layout_choice = st.selectbox("Layout", options=["3 columns", "2 columns"], index=0)

st.markdown("Define your structure fields:")

if "spec" not in st.session_state:
    st.session_state.spec = {
        "properties": {
            "title": {"type": "string", "required": True},
            "priority": {"type": "string"},
        }
    }

spec: Dict[str, Any] = st.session_state.spec

# Build columns based on layout
if layout_choice == "3 columns":
    col_left, col_mid, col_right = st.columns([1.1, 1.0, 1.1], gap="large")
else:
    col_left, col_right = st.columns([1.0, 1.2], gap="large")

# --- Left panel: Fields + JSON Schema ---
with col_left:
    with st.expander("Fields", expanded=True):
        cols = st.columns(3)
        with cols[0]:
            new_name = st.text_input("Field name", key="new_name")
        with cols[1]:
            new_type = st.selectbox(
                "Type",
                options=["string", "integer", "number", "boolean", "array", "object"],
                key="new_type",
            )
        with cols[2]:
            new_required = st.checkbox("Required", key="new_required")

        add = st.button("Add/Update Field")
        if add and new_name:
            spec.setdefault("properties", {})[new_name] = {"type": new_type, "required": bool(new_required)}
            st.toast(f"Field '{new_name}' saved", icon="✅")

        # List existing fields
        if spec.get("properties"):
            st.markdown("#### Current fields")
            for fname, fcfg in list(spec["properties"].items()):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1], gap="small")
                c1.write(fname)
                c2.code(fcfg.get("type", "string"))
                c3.write("required" if fcfg.get("required") else "optional")
                if c4.button("✖", key=f"rm_{fname}"):
                    del spec["properties"][fname]
                    st.rerun()

    st.markdown("### JSON Schema")
    SchemaModel = model_from_spec(spec)
    schema = SchemaModel.model_json_schema()
    st.code(json.dumps(schema, indent=2), language="json")

# Prepare default inputs
default_instructions = (
    "Extract a JSON object that matches the schema shown on the left. "
    "Only return the JSON object, with no extra commentary."
)
default_source = "Create a task titled 'Buy milk' with priority 'high'."

# --- Middle/Right panel(s): Inputs and Output ---
if layout_choice == "3 columns":
    # Middle: Inputs
    col_mid.markdown("### Inputs")
    instructions = col_mid.text_area("Instructions (preprompt)", value=default_instructions)
    source_text = col_mid.text_area("Source text", value=default_source)
    example_json = col_mid.text_area(
        "Example JSON (optional)", value="", placeholder='{"title": "Buy milk", "priority": "high"}'
    )
    run = col_mid.button("Generate JSON")

    if run:
        parts = []
        if instructions and instructions.strip():
            parts.append(instructions.strip())
        if example_json and example_json.strip():
            parts.append("Example JSON:\n" + example_json.strip())
        if source_text and source_text.strip():
            parts.append("Input:\n" + source_text.strip())
        prompt = "\n\n".join(parts).strip()

        try:
            result = generate(
                client=None,
                model=model,
                response_model=SchemaModel,
                prompt=prompt,
                max_retries=int(retries),
                provider=provider,  # type: ignore[arg-type]
            )
            st.session_state["last_output"] = result.model_dump_json(indent=2)
            st.session_state["last_error"] = None
        except Exception as e:
            st.session_state["last_error"] = str(e)
            st.session_state["last_output"] = None

    # Right: Output
    col_right.markdown("### Output")
    if st.session_state.get("last_error"):
        col_right.error(st.session_state["last_error"])
    elif st.session_state.get("last_output"):
        col_right.code(st.session_state["last_output"], language="json")
    else:
        col_right.info("Click Generate to see output here.")
else:
    # Right: Inputs and Output stacked
    col_right.markdown("### Try it")
    instructions = col_right.text_area("Instructions (preprompt)", value=default_instructions)
    source_text = col_right.text_area("Source text", value=default_source)
    example_json = col_right.text_area(
        "Example JSON (optional)", value="", placeholder='{"title": "Buy milk", "priority": "high"}'
    )
    run = col_right.button("Generate JSON")

    if run:
        parts = []
        if instructions and instructions.strip():
            parts.append(instructions.strip())
        if example_json and example_json.strip():
            parts.append("Example JSON:\n" + example_json.strip())
        if source_text and source_text.strip():
            parts.append("Input:\n" + source_text.strip())
        prompt = "\n\n".join(parts).strip()

        try:
            result = generate(
                client=None,
                model=model,
                response_model=SchemaModel,
                prompt=prompt,
                max_retries=int(retries),
                provider=provider,  # type: ignore[arg-type]
            )
            st.session_state["last_output"] = result.model_dump_json(indent=2)
            st.session_state["last_error"] = None
        except Exception as e:
            st.session_state["last_error"] = str(e)
            st.session_state["last_output"] = None

    col_right.markdown("### Output")
    if st.session_state.get("last_error"):
        col_right.error(st.session_state["last_error"])
    elif st.session_state.get("last_output"):
        col_right.code(st.session_state["last_output"], language="json")
    else:
        col_right.info("Click Generate to see output here.")
