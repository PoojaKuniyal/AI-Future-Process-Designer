from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProcessRunRequest(BaseModel):
    industry: str = Field(..., example="Retail")
    process_name: str = Field(..., example="Inventory Management")

class ProcessResponse(BaseModel):
    id: str
    industry: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class CurrentActivityResponse(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    system: Optional[str] = None
    problem: Optional[str] = None
    evidence: Optional[str] = None

    class Config:
        from_attributes = True

class FutureActivityResponse(BaseModel):
    id: str
    current_activity_id: Optional[str] = None
    name: str
    role: Optional[str] = None
    system: Optional[str] = None
    decision_type: str
    expected_benefit: Optional[str] = None
    risk: Optional[str] = None

    class Config:
        from_attributes = True

class AIOpportunityResponse(BaseModel):
    id: str
    opportunity_name: str
    description: str
    technology: Optional[str] = None
    expected_benefit: Optional[str] = None
    risk: Optional[str] = None

    class Config:
        from_attributes = True

class ResearchSourceResponse(BaseModel):
    id: str
    title: Optional[str] = None
    url: str
    retrieved_content: str

    class Config:
        from_attributes = True

class EvidenceAnalysisResponse(BaseModel):
    id: str
    source_id: str
    activity_id: Optional[str] = None
    problem: Optional[str] = None
    technology: Optional[str] = None
    how_it_works: Optional[str] = None
    applicability_why: Optional[str] = None
    parts_to_automate: Optional[str] = None
    human_control: Optional[str] = None
    systems_roles_affected: Optional[str] = None
    future_state_description: Optional[str] = None
    evidence_summary: Optional[str] = None
    source: Optional[ResearchSourceResponse] = None

    class Config:
        from_attributes = True

class EvidenceRelationshipResponse(BaseModel):
    id: str
    future_activity_id: str
    ai_opportunity_id: str
    evidence_analysis_id: str

    class Config:
        from_attributes = True

class ProcessDetailResponse(BaseModel):
    id: str
    industry: str
    name: str
    created_at: datetime
    current_activities: List[CurrentActivityResponse]
    future_activities: List[FutureActivityResponse]
    opportunities: List[AIOpportunityResponse]
    analyses: List[EvidenceAnalysisResponse]
    relationships: List[EvidenceRelationshipResponse]

    class Config:
        from_attributes = True

class SearchConfigUpdate(BaseModel):
    search_provider: str = Field(..., example="tavily")
