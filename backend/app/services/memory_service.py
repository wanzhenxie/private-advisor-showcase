import json
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Memory

# Small first-pass stopword list. It's intentionally lightweight for the MVP.
STOPWORDS = {
    "的", "了", "和", "是", "在", "我", "有", "也", "就", "都", "而", "及",
    "to", "the", "a", "an", "and", "or", "i", "my", "me", "is", "are", "of",
}

def tokenize(text: str) -> set[str]:
    # This is basic keyword extraction, not semantic search.
    # Chinese phrases can be a single token here, which limits recall.
    english = re.findall(r"[A-Za-z0-9_+-]{2,}", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return {x for x in english + chinese if x not in STOPWORDS}

# Only confirmed memories go into a new answer
# pending and active live in the same table; this query is what keeps
# unconfirmed suggestions out of the prompt.
# score is keyword overlap plus confidence
def retrieve_relevant_memories(db: Session, user_id: str, query: str, limit: int = 12) -> list[Memory]:
    # Only the current user's APPROVED memories may be used in model context.
    memories = db.scalars(
        select(Memory).where(Memory.user_id == user_id, Memory.status == "active")
    ).all()
    if not memories:
        return []
    query_tokens = tokenize(query)
    scored = []
    for memory in memories:
        tokens = tokenize(memory.content)
        tokens.update(str(k).lower() for k in (memory.keywords or []))
        overlap = len(query_tokens & tokens)
        if overlap > 0:
            scored.append((overlap * 10 + memory.confidence, memory))
    if not scored:
        # Fallback: include a few recent memories even when keywords don't match.
        # This helps small demos, but can also add irrelevant context.
        return sorted(memories, key=lambda m: m.updated_at, reverse=True)[:3]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:limit]]

def parse_json_object(text: str) -> dict:
    # The model may wrap JSON in markdown fences; handle that before parsing.
    # Invalid output should result in no candidate memories, not a chat crash.
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {"memories": []}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {"memories": []}

def dedupe_candidate(db: Session, user_id: str, content: str) -> bool:
    # Exact-text deduplication is enough to start, but paraphrases may slip through.
    normalized = re.sub(r"\\s+", " ", content.strip().lower())
    memories = db.scalars(select(Memory).where(Memory.user_id == user_id)).all()
    for memory in memories:
        existing = re.sub(r"\\s+", " ", memory.content.strip().lower())
        if existing == normalized:
            return True
    return False
