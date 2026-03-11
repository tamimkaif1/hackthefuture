import json
import os
from perception.models import SupplyRiskAssessment
from planning.models import MitigationPlan
from memory.models import DisruptionLog, ReflectionSummary

try:
    from langchain_core.prompts import PromptTemplate
    _LANGCHAIN_AVAILABLE = True
except Exception:
    _LANGCHAIN_AVAILABLE = False

from gemini_service import get_gemini_chat


def _mock_reflection(assessment: SupplyRiskAssessment, plan: MitigationPlan) -> ReflectionSummary:
    """Deterministic mock reflection (no API)."""
    return ReflectionSummary(
        summary_text=f"Mock: Event '{assessment.news_summary[:80]}...' was mitigated via {plan.chosen_scenario.action_type} (cost ${plan.chosen_scenario.estimated_cost_usd:,}).",
        key_takeaways="Mock: Maintain buffer stock for critical parts; consider alternate suppliers for high-exposure regions.",
    )


class ReflectionEngine:
    def __init__(self, log_file="past_disruptions.json", memory_chunks_file="memory_chunks.json", use_mock: bool = None):
        self.use_mock = use_mock
        if self.use_mock is None:
            try:
                self.use_mock = __import__("config", fromlist=["USE_MOCK_DATA"]).USE_MOCK_DATA
            except Exception:
                self.use_mock = True
        self.log_file = log_file
        self.memory_chunks_file = memory_chunks_file
        self.llm = None
        self.prompt = None
        if not self.use_mock and _LANGCHAIN_AVAILABLE:
            self.llm = get_gemini_chat(temperature=0.1)
            self.prompt = PromptTemplate(
            input_variables=["event", "plan"],
            template="""
            You are the Memory & Reflection System of the Supply Chain Agent.
            Your job is to summarize this entire disruption event into a 'smaller chunk' so it can be saved to the AI's long-term memory for future decision tree reasoning.
            
            EVENT DATA (Layer 1):
            {event}
            
            EXECUTED PLAN (Layer 3):
            {plan}
            
            Summarize what happened, what action we took, and the key takeaway for the future.
            
            Return ONLY a valid JSON object matching exactly:
            {{
                "summary_text": "string (Brief recap of event and action taken)",
                "key_takeaways": "string (What should we learn from this for next time)"
            }}
            """
            )

    def reflect_and_store(self, assessment: SupplyRiskAssessment, plan: MitigationPlan, auto_save: bool = False) -> ReflectionSummary:
        """Generate reflection, optionally save to disk, and return the reflection summary."""
        print(f"\n[Memory Engine] Generating reflection for event {assessment.signal_id}...")
        if self.use_mock:
            reflection = _mock_reflection(assessment, plan)
        else:
            try:
                chain = self.prompt | self.llm
                response = chain.invoke({
                    "event": assessment.model_dump_json(),
                    "plan": plan.model_dump_json()
                })
                clean_json = response.content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                reflection = ReflectionSummary(**data)
            except Exception as e:
                print(f"Memory LLM Error: {e}")
                reflection = _mock_reflection(assessment, plan)

        log = DisruptionLog(
            event_id=assessment.signal_id,
            original_risk=assessment,
            chosen_mitigation=plan,
            post_mortem_summary=reflection.summary_text + " | " + reflection.key_takeaways
        )

        print("\n*** MEMORY REFLECTION GENERATED ***")
        print(f"Summary: {reflection.summary_text}")
        print(f"Takeaways: {reflection.key_takeaways}")

        if auto_save:
            self._save_to_disk(log)
            self._save_memory_chunk(assessment, reflection)
            print("[System] Memory stored (auto-save in demo mode).")
        else:
            review = input("\nReview memory summary before saving? (y/n): ")
            if review.lower() == "y":
                self._save_to_disk(log)
                self._save_memory_chunk(assessment, reflection)
                print("[System] Memory stored locally in past_disruptions.json and memory_chunks.json")
            else:
                print("[System] Memory discarded.")

        return reflection

    def _save_memory_chunk(self, assessment: SupplyRiskAssessment, reflection: ReflectionSummary):
        """Append a short chunk for AI memory (condensed summary for future context)."""
        chunk = {
            "event_id": assessment.signal_id,
            "chunk": f"{reflection.summary_text} {reflection.key_takeaways}".strip()[:500],
        }
        history = []
        if os.path.exists(self.memory_chunks_file):
            try:
                with open(self.memory_chunks_file, "r") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []
        history.append(chunk)
        with open(self.memory_chunks_file, "w") as f:
            json.dump(history, f, indent=2)

    def _save_to_disk(self, log: DisruptionLog):
        history = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        history.append(json.loads(log.model_dump_json()))

        with open(self.log_file, "w") as f:
             json.dump(history, f, indent=2)

