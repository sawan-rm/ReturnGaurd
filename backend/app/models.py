import uuid
from datetime import datetime
from sqlalchemy import String, Float, Text, ForeignKey, Enum as SAEnum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum

# Notes:-
# "DeclarativeBase gives SQLAlchemy the foundation for declaring Python classes as database models."
# "Look at all models registered under Base and create the tables if they don't exist."
# Enum — a fixed list of allowed values.
class Base(DeclarativeBase):
    pass


# ── Enums ───────────────────────────────────
class Role(str, enum.Enum):
    customer = "customer"
    reviewer = "reviewer"
    admin = "admin"


class ReturnStatus(str, enum.Enum):
    submitted = "submitted"          # just created
    processing = "processing"        # agents working on it
    approved = "approved"            # auto-approved
    escalated = "escalated"          # needs human review
    denied = "denied"                # denied (human confirmed)
    completed = "completed"          # refund issued


class DecisionOutcome(str, enum.Enum):
    approve = "approve"
    escalate = "escalate"
    deny = "deny"


# ── Tables ──────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.customer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    returns: Mapped[list["ReturnRequest"]] = relationship(back_populates="order")


class ReturnRequest(Base):
    __tablename__ = "returns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ReturnStatus] = mapped_column(SAEnum(ReturnStatus), default=ReturnStatus.submitted)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    order: Mapped["Order"] = relationship(back_populates="returns")
    decision: Mapped["Decision | None"] = relationship(back_populates="return_request", uselist=False)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("returns.id"), unique=True, nullable=False)
    outcome: Mapped[DecisionOutcome] = mapped_column(SAEnum(DecisionOutcome), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    agent_trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    human_override: Mapped[bool | None] = mapped_column(default=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    return_request: Mapped["ReturnRequest"] = relationship(back_populates="decision")
