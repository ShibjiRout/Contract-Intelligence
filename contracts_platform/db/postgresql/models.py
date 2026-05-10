from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PlaybookRule(Base):
    __tablename__ = "playbook_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clause_type: Mapped[str] = mapped_column(String, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String, nullable=False)
    rule_type: Mapped[str] = mapped_column(String, nullable=False)  # REQUIRED / FORBIDDEN
    description: Mapped[str] = mapped_column(String, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    violation_message: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    versions: Mapped[list["RuleVersion"]] = relationship(
        "RuleVersion", back_populates="rule", cascade="all, delete-orphan"
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("playbook_rules.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    old_value: Mapped[dict] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict] = mapped_column(JSON, nullable=True)
    changed_by: Mapped[str] = mapped_column(String, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    rule: Mapped["PlaybookRule"] = relationship("PlaybookRule", back_populates="versions")


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ClauseTypeRegistry(Base):
    __tablename__ = "clause_type_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clause_type: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RuleWeight(Base):
    __tablename__ = "rule_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jurisdiction: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    postgresql_weight: Mapped[float] = mapped_column(Float, nullable=False)
    qdrant_weight: Mapped[float] = mapped_column(Float, nullable=False)
    neo4j_weight: Mapped[float] = mapped_column(Float, nullable=False)
