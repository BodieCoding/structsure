from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class SchemaRecord(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    schema_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RunRecord(BaseModel):
    id: Optional[int] = None
    schema_id: int
    prompt: str
    output_json: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
