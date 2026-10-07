import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Decision

def compute_decision_hash(decision: Decision) -> str:
    """
    Computes a SHA-256 hash for a decision to make it tamper-evident.
    Combines key fields + the hash of the previous decision in the chain.
    """
    data = (
        f"{decision.id}"
        f"{decision.return_id}"
        f"{decision.outcome.value if decision.outcome else ''}"
        f"{decision.explanation}"
        f"{decision.human_override}"
        f"{decision.prev_hash or ''}"
    )
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

async def get_prev_hash(session: AsyncSession) -> str:
    """
    Gets the hash of the most recently inserted decision to chain the next one.
    Returns 'GENESIS' if this is the first decision in the database.
    """
    result = await session.execute(
        select(Decision).order_by(Decision.decided_at.desc(), Decision.id.desc()).limit(1)
    )
    last_decision = result.scalar_one_or_none()
    
    if not last_decision:
        return "GENESIS"
    
    # We recompute the hash of the last decision instead of just returning its prev_hash.
    # This forms the unbroken chain: H(current) = SHA256(data + H(prev))
    return compute_decision_hash(last_decision)
