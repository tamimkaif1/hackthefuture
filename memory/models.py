from pydantic import BaseModel
from perception.models import SupplyRiskAssessment
from planning.models import MitigationPlan

class DisruptionLog(BaseModel):
    event_id: str
    original_risk: SupplyRiskAssessment
    chosen_mitigation: MitigationPlan
    post_mortem_summary: str
    
class ReflectionSummary(BaseModel):
    summary_text: str
    key_takeaways: str
