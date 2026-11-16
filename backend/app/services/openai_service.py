from dataclasses import dataclass
from typing import Any
from openai import OpenAI
from ..config import get_settings
from .memory_service import parse_json_object

settings = get_settings()

# Keep the returned text and usage numbers together; both matter for the UI.
@dataclass
class ModelResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置。请在 .env 中填写 OpenAI API key。")
    return OpenAI(api_key=settings.openai_api_key)

def _usage(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if not usage:
        return 0, 0
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)

def generate_advice(instructions: str, input_items: list[dict]) -> ModelResult:
    # One model call generates the answer. Memory extraction is a separate call.
    response = _client().responses.create(
        model=settings.openai_model,
        reasoning={"effort": "low"},
        instructions=instructions,
        input=input_items,
    )
    input_tokens, output_tokens = _usage(response)
    return ModelResult(response.output_text.strip(), input_tokens, output_tokens, settings.openai_model)

def extract_memory_candidates(user_text: str) -> tuple[list[dict], ModelResult]:
    # Deliberately use the user's original words rather than treating an AI reply
    # as a reliable new fact about the user.
    instructions = """
你是一个严格的长期记忆提取器。只分析用户自己的原话。
只提取用户明确陈述的、未来数周/月/年仍可能有价值的事实、偏好、目标、长期计划、工作/学习背景或重要关系信息。
绝不提取你的推断、临时情绪、单次任务、密码、API key、身份证号、银行卡号等秘密或用户没说过的事情。

输出纯 JSON：
{"memories":[{"category":"preference|goal|education|work|family|project|location|other","content":"简洁事实","confidence":0.9,"keywords":["关键词"]}]}
没有值得保存的内容则输出 {"memories":[]}。最多3条。
""".strip()
    response = _client().responses.create(
        model=settings.openai_model,
        reasoning={"effort": "low"},
        instructions=instructions,
        input=user_text,
    )
    parsed = parse_json_object(response.output_text)
    candidates = parsed.get("memories", [])
    if not isinstance(candidates, list):
        candidates = []
    allowed = {"preference","goal","education","work","family","project","location","other"}
    cleaned = []
    # Validate the model's structured output before passing it to the database.
    for c in candidates[:3]:
        if not isinstance(c, dict):
            continue
        content = str(c.get("content", "")).strip()
        if not content:
            continue
        category = str(c.get("category", "other"))
        if category not in allowed:
            category = "other"
        try:
            confidence = min(1.0, max(0.0, float(c.get("confidence", 0.9))))
        except (TypeError, ValueError):
            confidence = 0.9
        keywords = c.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        cleaned.append({
            "category": category,
            "content": content[:2000],
            "confidence": confidence,
            "keywords": [str(k)[:80] for k in keywords[:8] if str(k).strip()],
        })
    input_tokens, output_tokens = _usage(response)
    return cleaned, ModelResult(response.output_text, input_tokens, output_tokens, settings.openai_model)
