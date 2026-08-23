import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from backend.app.database import Base

class Process(Base):
    __tablename__ = "processes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    industry = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    current_activities = relationship("CurrentActivity", back_populates="process", cascade="all, delete-orphan")
    queries = relationship("ResearchQuery", back_populates="process", cascade="all, delete-orphan")
    opportunities = relationship("AIOpportunity", back_populates="process", cascade="all, delete-orphan")
    future_activities = relationship("FutureActivity", back_populates="process", cascade="all, delete-orphan")


class CurrentActivity(Base):
    __tablename__ = "current_activities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    system = Column(String, nullable=True)
    problem = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)  # Contextual evidence if seeded/found
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    process = relationship("Process", back_populates="current_activities")
    evidence_analyses = relationship("EvidenceAnalysis", back_populates="activity")
    future_activities = relationship("FutureActivity", back_populates="current_activity")


class ResearchQuery(Base):
    __tablename__ = "research_queries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    intent = Column(String, nullable=True)  # tech, automation, AI, emerging, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    process = relationship("Process", back_populates="queries")
    sources = relationship("ResearchSource", back_populates="query", cascade="all, delete-orphan")


class ResearchSource(Base):
    __tablename__ = "research_sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query_id = Column(String, ForeignKey("research_queries.id"), nullable=True)
    process_id = Column(String, ForeignKey("processes.id"), nullable=True)
    title = Column(String, nullable=True)
    url = Column(String, nullable=False)
    retrieved_content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    query = relationship("ResearchQuery", back_populates="sources")
    evidence_analyses = relationship("EvidenceAnalysis", back_populates="source")


class EvidenceAnalysis(Base):
    __tablename__ = "evidence_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, ForeignKey("research_sources.id"), nullable=False)
    activity_id = Column(String, ForeignKey("current_activities.id"), nullable=True)
    problem = Column(Text, nullable=True)
    technology = Column(String, nullable=True)
    how_it_works = Column(Text, nullable=True)
    applicability_why = Column(Text, nullable=True)
    parts_to_automate = Column(Text, nullable=True)
    human_control = Column(Text, nullable=True)
    systems_roles_affected = Column(Text, nullable=True)
    future_state_description = Column(Text, nullable=True)
    evidence_summary = Column(Text, nullable=True)
    embedding = Column(Vector(384), nullable=True)  # Embedding from sentence-transformers MiniLM-L6
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source = relationship("ResearchSource", back_populates="evidence_analyses")
    activity = relationship("CurrentActivity", back_populates="evidence_analyses")
    relationships = relationship("EvidenceRelationship", back_populates="evidence_analysis", cascade="all, delete-orphan")


class AIOpportunity(Base):
    __tablename__ = "ai_opportunities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    opportunity_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    technology = Column(String, nullable=True)
    expected_benefit = Column(Text, nullable=True)
    risk = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    process = relationship("Process", back_populates="opportunities")
    relationships = relationship("EvidenceRelationship", back_populates="ai_opportunity", cascade="all, delete-orphan")


class FutureActivity(Base):
    __tablename__ = "future_activities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    current_activity_id = Column(String, ForeignKey("current_activities.id"), nullable=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    system = Column(String, nullable=True)
    decision_type = Column(String, nullable=False)  # Fully automated, AI-assisted, Human-in-the-loop, Human decision
    expected_benefit = Column(Text, nullable=True)
    risk = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    process = relationship("Process", back_populates="future_activities")
    current_activity = relationship("CurrentActivity", back_populates="future_activities")
    relationships = relationship("EvidenceRelationship", back_populates="future_activity", cascade="all, delete-orphan")


class EvidenceRelationship(Base):
    __tablename__ = "evidence_relationships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    future_activity_id = Column(String, ForeignKey("future_activities.id"), nullable=False)
    ai_opportunity_id = Column(String, ForeignKey("ai_opportunities.id"), nullable=False)
    evidence_analysis_id = Column(String, ForeignKey("evidence_analyses.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    future_activity = relationship("FutureActivity", back_populates="relationships")
    ai_opportunity = relationship("AIOpportunity", back_populates="relationships")
    evidence_analysis = relationship("EvidenceAnalysis", back_populates="relationships")
