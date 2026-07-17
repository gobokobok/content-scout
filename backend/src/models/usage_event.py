import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk

# Layer-1 internal cost ledger (D12/D26). `kind` is a free string by design —
# new resource kinds (gemini_*, storage_gb_month, compute_alloc, ...) must not
# require a migration. Current kinds: apify_result, claude_input_tokens,
# claude_output_tokens.
KIND_APIFY_RESULT = "apify_result"
KIND_CLAUDE_INPUT_TOKENS = "claude_input_tokens"
KIND_CLAUDE_OUTPUT_TOKENS = "claude_output_tokens"


class UsageEvent(UuidPk, CreatedAt, Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
