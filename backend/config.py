"""Paths, policy thresholds and feature flags in one place."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CASES_DIR = DATA / "cases"
INDEX_DIR = DATA / "index"
LOG_DIR = DATA / "logs"
DB_PATH = DATA / "rexetive.db"
CHECKPOINT_DB = DATA / "checkpoints.db"
TRACE_LOG = LOG_DIR / "trace.jsonl"

# Policy gate (pure Python, see agent/policy.py). Scores are out of 40 (4 judges x 10).
ACCEPT_MIN_TOTAL = 30
REJECT_BELOW_TOTAL = 26
MAX_DISAGREEMENT = 0.4      # spread of judges' normalised (0..1) scores above which a human decides
DUPLICATE_SIMILARITY = 0.97   # measured: distinct same-case analyses reach 0.94, true near-copies >= 0.998 (see README)
EVIDENCE_K = 6

# Analytics: the only tables text-to-SQL may read.
ANALYTICS_TABLES = ["users", "submissions", "reviews", "credentials", "reputation"]

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
SUI_MOCK = os.getenv("SUI_MOCK", "1") != "0"
JWT_SECRET = os.getenv("JWT_SECRET_KEY") or "dev-only-secret-change-me"
JWT_ALGORITHM = "HS256"
JWT_MINUTES = 120
