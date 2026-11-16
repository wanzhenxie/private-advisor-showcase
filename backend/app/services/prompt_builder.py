from ..models import Profile, Memory, Message

BASE_INSTRUCTIONS = """
你是“私人智囊”，目标是基于用户明确提供的信息，给出有帮助、具体、诚实且不过度自信的建议。

原则：
1. 不要把推测包装成事实。
2. 若关键信息不足，明确指出缺失信息；只有必要时才追问。
3. 使用提供的长期记忆进行个性化，但不要机械重复用户资料。
4. 如果长期记忆与用户当前陈述冲突，以当前陈述优先，并提示可能存在变化。
5. 医疗、法律、财务等高风险领域要明确不确定性和适当的专业求助边界。
6. 不要声称自己拥有用户未提供的信息。
7. 回答默认使用用户正在使用的语言。
""".strip()

def build_instructions(profile: Profile | None, memories: list[Memory]) -> str:
    # Profile preferences and confirmed memory become context, not new user turns.
    parts = [BASE_INSTRUCTIONS]
    if profile:
        parts.append(
            "\n用户偏好设置：\n"
            f"- locale: {profile.locale}\n"
            f"- timezone: {profile.timezone}\n"
            f"- advisor_preferences: {profile.advisor_preferences}"
        )
    if memories:
        memory_text = "\n".join(f"- [{m.category}] {m.content}" for m in memories)
        parts.append("\n以下是用户已经确认的长期记忆。只在相关时使用：\n" + memory_text)
    return "\n".join(parts)

def build_input(recent_messages: list[Message], new_user_message: str) -> list[dict]:
    # Keep only the latest messages to avoid sending the full database history.
    items = []
    for message in recent_messages[-12:]:
        if message.role in {"user", "assistant"}:
            items.append({"role": message.role, "content": message.content})
    items.append({"role": "user", "content": new_user_message})
    return items
