from pydantic import BaseModel, Field
from typing import List, Optional

class NewsSignal(BaseModel):
    id: str
    headline: str
    content: str
    source: str
    timestamp: str
    location: Optional[str] = None
    affected_entities: Optional[List[str]] = Field(default_factory=list)

class ERPInventorySnapshot(BaseModel):
    part_id: str
    description: str
    current_stock: int
    buffer_min: int
    primary_supplier: str
    supplier_location: str
    lead_time_days: int

class SupplyRiskAssessment(BaseModel):
    signal_id: str
    news_summary: str = Field(description="A concise 1-paragraph summary of the news event")
    risk_score: int = Field(description="Risk score from 1 (low) to 10 (high)")
    probability: str = Field(description="Low, Medium, or High probability of disruption")
    impact_level: str = Field(description="Low, Medium, or High business impact")
    affected_parts: List[str] = Field(description="List of part IDs potentially affected")
    recommended_mitigation: str = Field(description="Brief mitigation strategy recommendation")
    rationale: str = Field(description="Explainable reasoning trace for the assessment")
