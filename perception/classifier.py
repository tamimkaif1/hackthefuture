import os
import json
from typing import List
from dotenv import load_dotenv
from perception.models import NewsSignal, ERPInventorySnapshot, SupplyRiskAssessment

load_dotenv()

try:
    from langchain_core.prompts import PromptTemplate
    _LANGCHAIN_AVAILABLE = True
except Exception:
    _LANGCHAIN_AVAILABLE = False

from gemini_service import get_gemini_chat


def _mock_assessment(news: NewsSignal, inventory_context: List[ERPInventorySnapshot]) -> SupplyRiskAssessment:
    """Deterministic mock assessment (no API). Distinct scores per event type."""
    affected = [p.part_id for p in inventory_context] if inventory_context else []
    if not affected and news.location:
        affected = ["IC-7NM-001"]  # fallback for demo

    # Assign distinct risk scores based on headline keywords for visual variety
    headline_lower = news.headline.lower()
    if any(w in headline_lower for w in ["typhoon", "hurricane", "earthquake", "flood"]):
        risk_score, probability, impact = 9, "High", "High"
        mitigation = "Immediately activate backup suppliers; expedite air freight for critical parts."
    elif any(w in headline_lower for w in ["fire", "explosion", "factory", "fab"]):
        risk_score, probability, impact = 8, "High", "High"
        mitigation = "Expedite alternate shipping or tap secondary suppliers."
    elif any(w in headline_lower for w in ["strike", "red sea", "canal", "geopolit", "sanction"]):
        risk_score, probability, impact = 6, "Medium", "Medium"
        mitigation = "Monitor rerouting options; reassess lead times."
    else:
        risk_score, probability, impact = 5, "Medium", "Medium"
        mitigation = "Monitor situation and prepare contingency plans."

    return SupplyRiskAssessment(
        signal_id=news.id,
        news_summary=f"Mock summary: Disruption at {news.location or 'region'} impacting {news.headline}.",
        risk_score=risk_score,
        probability=probability,
        impact_level=impact,
        affected_parts=affected,
        recommended_mitigation=mitigation,
        rationale="Mock: Event impacts primary supplier location; buffer and lead times indicate high exposure.",
    )



class RiskClassifier:
    def __init__(self, use_mock: bool = None):
        self.use_mock = use_mock if use_mock is not None else __import__("config", fromlist=["USE_MOCK_DATA"]).USE_MOCK_DATA
        self.llm = None
        if not self.use_mock and _LANGCHAIN_AVAILABLE:
            self.llm = get_gemini_chat(temperature=0.2)
        
        # We use a system prompt that enforces structured reasoning
        self.prompt = None
        if not self.use_mock and _LANGCHAIN_AVAILABLE:
            from langchain_core.prompts import PromptTemplate
            self.prompt = PromptTemplate(
                input_variables=["news_signal", "erp_context"],
                template="""
                You are an expert Supply Chain Risk Analyst for a mid-market manufacturing company.
                You need to assess the operational risk of an incoming news event based on our current inventory levels.

                NEW EVENT:
                {news_signal}

                OUR CURRENT INVENTORY EXPOSURE:
                {erp_context}

                Assess the probability of this event disrupting our supply chain and the business impact based on the inventory buffer and lead times.
                Provide your response as a valid JSON object matching this schema exactly:
                {{
                    "signal_id": "string (use the id from the news event)",
                    "news_summary": "string (a concise 1-sentence summary of what happened)",
                    "risk_score": integer (1-10),
                    "probability": "Low" | "Medium" | "High",
                    "impact_level": "Low" | "Medium" | "High",
                    "affected_parts": ["list", "of", "part_ids"],
                    "recommended_mitigation": "string (brief action, e.g., 'Expedite shipping', 'Reroute via air')",
                    "rationale": "string (explain why based on the buffer vs lead time)"
                }}
                """
            )

    def assess_risk(self, news: NewsSignal, inventory_context: List[ERPInventorySnapshot]) -> SupplyRiskAssessment:
        """Takes a news signal and relevant ERP context, and returns a structured risk assessment."""
        if self.use_mock:
            print(f"\n[Classifier] Mock mode: generating deterministic assessment for {news.headline}...")
            return _mock_assessment(news, inventory_context)

        news_text = f"Headline: {news.headline}\nDetails: {news.content}\nLocation: {news.location}"
        if not inventory_context:
            erp_text = "No direct inventory exposure found for this location."
        else:
            erp_text = ""
            for item in inventory_context:
                erp_text += (f"- Part {item.part_id} ({item.description}): "
                            f"Stock={item.current_stock}, Min Buffer={item.buffer_min}, "
                            f"Lead Time={item.lead_time_days} days. Supplier: {item.primary_supplier}\n")

        try:
            chain = self.prompt | self.llm
            print(f"\n[Classifier] Analyzing risk for event: {news.headline}...")
            response = chain.invoke({"news_signal": news_text, "erp_context": erp_text})
            clean_json = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            return SupplyRiskAssessment(**data)
        except Exception as e:
            print(f"LLM API Error: {e}. Falling back to mock assessment.")
            return _mock_assessment(news, inventory_context)
