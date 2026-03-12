"""
SQLAlchemy database models for the referral state manager system.

This module defines the database schema for:
- referral_state_manager: Main referral records with state and mermaid scripts
- referral_state_history: Audit trail of all state transitions
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ReferralStateManager(Base):
    """
    Main table for storing referral records with their current state and mermaid diagrams.
    
    This table stores:
    - Referral ID (primary key)
    - Current state
    - Attributes (flexible JSONB field)
    - Mermaid script (for frontend visualization)
    - Metadata (additional JSONB for extra data)
    - Audit fields (timestamps, user tracking)
    """

    __tablename__ = "referral_state_manager"

    referral_id = Column(String(255), primary_key=True, nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    attributes = Column(JSONB, nullable=True, default=dict)
    mermaid_script = Column(Text, nullable=True)
    meta_data = Column("metadata", JSONB, nullable=True, default=dict)  # Column name is 'metadata' in DB
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)

    # Relationship to state history
    state_history = relationship(
        "ReferralStateHistory",
        back_populates="referral",
        cascade="all, delete-orphan",
        order_by="ReferralStateHistory.transitioned_at",
    )

    def __repr__(self) -> str:
        return f"<ReferralStateManager(referral_id={self.referral_id}, state={self.state})>"


class ReferralStateHistory(Base):
    """
    Audit trail table for tracking all state transitions.
    
    Each row represents a single state change event, providing a complete
    history of how a referral moved through different states.
    """

    __tablename__ = "referral_state_history"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    referral_id = Column(
        String(255),
        ForeignKey("referral_state_manager.referral_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state = Column(String(50), nullable=True)  # NULL for initial state
    to_state = Column(String(50), nullable=False)
    transitioned_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    transitioned_by = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)  # Optional reason for state change

    # Relationship back to referral
    referral = relationship("ReferralStateManager", back_populates="state_history")

    def __repr__(self) -> str:
        return (
            f"<ReferralStateHistory(id={self.id}, referral_id={self.referral_id}, "
            f"from_state={self.from_state}, to_state={self.to_state})>"
        )
