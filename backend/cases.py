"""Case files and the evidence index.

Concept: v1 judged submissions against a short case description plus the model's general
knowledge, which is how an LLM ends up "confirming" plausible-sounding theories that the
evidence actually contradicts. v2 gives every case an evidence pack (incident report,
timeline/access logs, witness statements, analyst notes, one document with a deliberate
contradiction) and indexes it with ragcore. Judges only see retrieved evidence, wrapped as
<evidence id=E3> blocks, and every flag must cite evidence ids.

Each evidence document has a stable evidence_id (E1..E7) in its front matter. Chunks inherit
it, so citations stay stable even if chunking changes. Metadata: case_id, doc_type, date.

case.json also holds the rubric used by the offline (no-LLM) judges: key facts with the
evidence that proves them, "traps" (claims the evidence contradicts) and solution keywords.
"""
from __future__ import annotations

import json
from functools import lru_cache

from config import CASES_DIR, EVIDENCE_K, INDEX_DIR
from ragcore.chunker import Chunk, chunk_markdown
from ragcore.pipeline import Indexes, RagPipeline


def parse_front_matter(text: str) -> tuple[dict, str]:
    _, header, body = text.split("---", 2)
    meta = {}
    for line in header.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.lstrip()


@lru_cache(maxsize=1)
def load_cases() -> dict[int, dict]:
    cases = {}
    for folder in sorted(CASES_DIR.iterdir()):
        if not (folder / "case.json").exists():
            continue
        case = json.loads((folder / "case.json").read_text(encoding="utf-8"))
        case["evidence"] = []
        for path in sorted(folder.glob("E*.md")):
            meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
            case["evidence"].append({**meta, "case_id": int(meta["case_id"]), "body": body, "file": path.name})
        cases[case["id"]] = case
    return cases


def public_case(case: dict) -> dict:
    """What the frontend sees: no rubric (key facts / traps would give answers away)."""
    return {"id": case["id"], "title": case["title"], "description": case["summary"],
            "createdDate": case["createdDate"],
            "evidence": [{"evidence_id": e["evidence_id"], "title": e["title"], "doc_type": e["doc_type"],
                          "date": e["date"], "body": e["body"]} for e in case["evidence"]]}


def all_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for case in load_cases().values():
        for ev in case["evidence"]:
            meta = {"case_id": case["id"], "evidence_id": ev["evidence_id"], "doc_type": ev["doc_type"],
                    "date": ev["date"], "title": ev["title"], "source_url": f"case/{case['id']}/{ev['evidence_id']}"}
            chunks += chunk_markdown(f"c{case['id']}-{ev['evidence_id']}", ev["body"], meta)
    return chunks


@lru_cache(maxsize=1)
def get_indexes() -> Indexes:
    return Indexes(all_chunks(), INDEX_DIR, collection="rexetive_evidence")


def retrieve_evidence(case_id: int, text: str, k: int = EVIDENCE_K) -> list[dict]:
    """Hybrid retrieval restricted to one case (metadata filter), no rewrite (the submission
    is self-contained), reranked. Returns one entry per evidence document, best first."""
    pipe = RagPipeline(get_indexes(), use_rewrite=False, abstain_threshold=0.0)
    res = pipe.retrieve(text[:1500], where={"case_id": case_id}, k=k)
    seen, out = set(), []
    for p in res.passages:
        eid = p.metadata["evidence_id"]
        if eid in seen:
            continue
        seen.add(eid)
        out.append({"evidence_id": eid, "title": p.metadata["title"], "doc_type": p.metadata["doc_type"],
                    "date": p.metadata["date"], "text": p.text, "score": round(p.score, 4), "chunk_id": p.id})
    return out
