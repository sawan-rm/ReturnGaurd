from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from app.models import ReturnStatus, DecisionOutcome


# ── Return ──────────────────────────────────

class ReturnCreate(BaseModel):
    order_id: UUID
    reason: str


class ReturnRead(BaseModel):
    id: UUID
    order_id: UUID
    reason: str
    photo_url: str | None
    status: ReturnStatus
    risk_score: float | None
    created_at: datetime
    updated_at: datetime

    # “Pydantic is allowed to get data from an object's attributes.”
    # from_attributes=True tells Pydantic: “You don't need to give me a dictionary. I can read the values directly from the SQLAlchemy object's attributes.”
    model_config = {"from_attributes": True}


# ── Decision ───────────────────────────────

class DecisionRead(BaseModel):
    id: UUID
    return_id: UUID
    outcome: DecisionOutcome
    explanation: str
    human_override: bool | None
    decided_at: datetime

    model_config = {"from_attributes": True}


# ── Return with Decision (for detail view) ─

class ReturnDetail(ReturnRead):
    decision: DecisionRead | None = None

class OrderRead(BaseModel):
    id: UUID
    user_id: UUID
    product_name: str
    product_category: str
    amount: float
    ordered_at: datetime

    model_config = {"from_attributes": True}
