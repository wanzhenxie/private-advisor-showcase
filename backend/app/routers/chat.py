from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, Conversation, Message, Memory, UsageEvent
from ..schemas import ConversationCreate, ConversationOut, MessageCreate, MessageOut, ChatReply
from ..services.memory_service import retrieve_relevant_memories, dedupe_candidate
from ..services.openai_service import generate_advice, extract_memory_candidates
from ..services.prompt_builder import build_instructions, build_input

router = APIRouter(prefix="/api/conversations", tags=["chat"])
# Record the advice call separately from memory extraction,
# so the usage page can show the two kinds of model calls.

def owned_conversation(db: Session, user_id: str, conversation_id: str) -> Conversation:
    # Include user_id in the query so someone cannot read another account's chat
    # just by knowing a conversation ID.
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conversation

@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = Conversation(user_id=current_user.id, title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

@router.get("", response_model=list[ConversationOut])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(db.scalars(stmt).all())

@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(db, current_user.id, conversation_id)
    return conversation.messages

@router.post("/{conversation_id}/messages", response_model=ChatReply)
def send_message(
    conversation_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(db, current_user.id, conversation_id)
    # Send a bounded window of chat history to keep prompt size under control.
    recent_history = list(conversation.messages[-12:])

    # Confirmed long-term memories are added separately from recent messages.
    relevant_memories = retrieve_relevant_memories(
        db=db,
        user_id=current_user.id,
        query=payload.content,
    )
    instructions = build_instructions(current_user.profile, relevant_memories)
    input_items = build_input(recent_history, payload.content)

    try:
        advice_result = generate_advice(instructions, input_items)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"模型调用失败：{type(exc).__name__}") from exc

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.content,
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=advice_result.text,
    )
    db.add_all([user_message, assistant_message])

    db.add(
        # The frontend needs both pieces: the answer, and any new pending memories.
        # if extraction failed above, memory_candidates is just an empty list
        UsageEvent(
            user_id=current_user.id,
            kind="advice",
            model=advice_result.model,
            input_tokens=advice_result.input_tokens,
            output_tokens=advice_result.output_tokens,
        )
    )

    # Pending suggestions are written only after the model answer is available.
    memory_candidates: list[Memory] = []

    # A memory-extraction failure must never break the main chat response.
    try:
        candidates, memory_usage = extract_memory_candidates(payload.content)
        db.add(
            UsageEvent(
                user_id=current_user.id,
                kind="memory_extraction",
                model=memory_usage.model,
                input_tokens=memory_usage.input_tokens,
                output_tokens=memory_usage.output_tokens,
            )
        )
        for candidate in candidates:
            if dedupe_candidate(db, current_user.id, candidate["content"]):
                continue
            memory = Memory(
                user_id=current_user.id,
                category=candidate["category"],
                content=candidate["content"],
                source="user_statement",
                confidence=candidate["confidence"],
                status="pending",
                keywords=candidate["keywords"],
            )
            db.add(memory)
            memory_candidates.append(memory)
    except Exception:
        # Intentionally best-effort in v0.1: chat still succeeds without memories.
        # TODO: Log a sanitized error here so debugging isn't silent.
        pass

    if conversation.title == "新对话" and len(recent_history) == 0:
        conversation.title = payload.content.strip().replace("\n", " ")[:60] or "新对话"

    db.commit()
    db.refresh(assistant_message)
    for memory in memory_candidates:
        db.refresh(memory)

    return ChatReply(
        assistant_message=assistant_message,
        memory_candidates=memory_candidates,
    )
