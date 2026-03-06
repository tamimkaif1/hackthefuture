from pydantic import BaseModel, Field
from typing import List

class ScenarioSimulation(BaseModel):
    scenario_id: str
    action_type: str = Field(description="e.g., 'Expedite Air Freight', 'Re-source from Mexico', 'Do Nothing'")
    estimated_cost_usd: int
    service_level_impact: str = Field(description="e.g., 'Maintained', 'Delayed 2 weeks', 'Critical Failure'")
    resilience_score: int = Field(description="Score out of 10 representing how robust this option is")

class MitigationPlan(BaseModel):
    plan_id: str
    chosen_scenario: ScenarioSimulation
    supplier_reallocation_target: str = Field(default="N/A", description="Supplier to move orders to")
    buffer_stock_adjustment: int = Field(default=0, description="Amount to increase buffer stock by")
    reasoning_tree: str = Field(description="Why this plan was selected over alternatives")
