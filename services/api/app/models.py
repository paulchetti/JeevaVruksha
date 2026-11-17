from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    JSON,
    MetaData,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def new_id() -> str:
    return str(uuid4())


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'suspended', 'closed')", name="status"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    oidc_issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    oidc_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(200))
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    __table_args__ = (
        UniqueConstraint("oidc_issuer", "oidc_subject", name="uq_users_oidc_identity"),
        CheckConstraint("status IN ('active', 'disabled')", name="status"),
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'faculty', 'college_admin', 'clinical_content_reviewer')",
            name="role",
        ),
        CheckConstraint("status IN ('active', 'suspended', 'revoked')", name="status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('trialing', 'active', 'past_due', 'canceled', 'expired')",
            name="status",
        ),
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at", name="subscription_period"
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    plan_code: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Cohort(Base):
    __tablename__ = "cohorts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_cohorts_tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_cohorts_tenant_name"),
        ForeignKeyConstraint(
            ["tenant_id", "created_by_user_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProtocolPack(Base):
    __tablename__ = "protocol_packs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_protocol_packs_tenant_id"),
        UniqueConstraint("tenant_id", "version", name="uq_protocol_packs_tenant_version"),
        CheckConstraint(
            "status IN ('draft', 'in_review', 'published', 'retired')", name="status"
        ),
        CheckConstraint(
            "review_status IN ('pending_local_review', 'in_review', 'approved', 'rejected')",
            name="review_status",
        ),
        CheckConstraint(
            "status != 'published' OR "
            "(review_status = 'approved' AND effective_date IS NOT NULL "
            "AND reviewed_by_user_id IS NOT NULL)",
            name="published_pack_reviewed",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "reviewed_by_user_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    jurisdiction_code: Mapped[str] = mapped_column(String(20), nullable=False, default="IN")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending_local_review"
    )
    source_references: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    change_history: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    effective_date: Mapped[date | None] = mapped_column(Date)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClinicalCase(Base):
    __tablename__ = "clinical_cases"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_clinical_cases_tenant_id"),
        UniqueConstraint(
            "tenant_id", "slug", "case_version", name="uq_clinical_cases_tenant_slug_version"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "protocol_pack_id"],
            ["protocol_packs.tenant_id", "protocol_packs.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('draft', 'in_review', 'published', 'retired')", name="status"
        ),
        CheckConstraint(
            "review_status IN ('pending_local_review', 'in_review', 'approved', 'rejected')",
            name="review_status",
        ),
        CheckConstraint("duration_minutes > 0", name="duration_minutes_positive"),
        CheckConstraint(
            "status != 'published' OR "
            "(review_status = 'approved' AND effective_date IS NOT NULL "
            "AND reviewed_by_user_id IS NOT NULL)",
            name="published_case_reviewed",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "reviewed_by_user_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    protocol_pack_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    case_version: Mapped[str] = mapped_column(String(80), nullable=False)
    protocol_pack_version: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending_local_review"
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_references: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    change_history: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    effective_date: Mapped[date | None] = mapped_column(Date)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "case_id"],
            ["clinical_cases.tenant_id", "clinical_cases.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "cohort_id"],
            ["cohorts.tenant_id", "cohorts.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "assigned_by_user_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "case_id", "cohort_id", name="uq_case_assignments_scope"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    cohort_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    assigned_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_attempts_tenant_id"),
        UniqueConstraint(
            "tenant_id", "user_id", "idempotency_key", name="uq_attempts_idempotency"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "case_id"],
            ["clinical_cases.tenant_id", "clinical_cases.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "cohort_id"],
            ["cohorts.tenant_id", "cohorts.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')", name="status"
        ),
        CheckConstraint("score IS NULL OR score >= 0", name="score_nonnegative"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    case_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    cohort_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    case_version: Mapped[str] = mapped_column(String(80), nullable=False)
    protocol_pack_version: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    score: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AttemptEvent(Base):
    __tablename__ = "attempt_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "attempt_id"],
            ["attempts.tenant_id", "attempts.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("tenant_id", "attempt_id", "sequence_number", name="uq_attempt_event_order"),
        UniqueConstraint(
            "tenant_id", "attempt_id", "idempotency_key", name="uq_attempt_event_idempotency"
        ),
        CheckConstraint("sequence_number > 0", name="sequence_number_positive"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "attempt_id"],
            ["attempts.tenant_id", "attempts.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "user_id", "badge_id", name="uq_user_badges_award"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    badge_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("badges.id", ondelete="RESTRICT"), nullable=False
    )
    attempt_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "invited_by_user_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "role IN ('student', 'faculty', 'college_admin', 'clinical_content_reviewer')",
            name="role",
        ),
        UniqueConstraint("tenant_id", "token_digest", name="uq_invitations_tenant_token"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    invited_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "(actor_type = 'system' AND actor_user_id IS NULL) OR "
            "(actor_type = 'user' AND actor_user_id IS NOT NULL)",
            name="actor_type",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("tenants.id", ondelete="SET NULL")
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
