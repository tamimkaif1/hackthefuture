"""Central config: mock-only mode (no real API calls). All data is deterministic mock data."""

import os
from dotenv import load_dotenv

load_dotenv()

# When True, classifier, planning, and reflection use deterministic mock data only (no Gemini/API).
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "1").strip().lower() in ("1", "true", "yes")
