from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, Memory
from ..schemas import MemoryCreate, MemoryOut, MemoryUpdate

router = APIRouter(prefix="/api/memories", tags=["memories"])

def owned_memory(db: Session, user_id: str, memory_id: str) -> Memory:
    # Scope memory lookups to the signed-in user (same idea as conversations).
    memory = db.scalar(select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id))
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return memory

@router.get("", response_model=list[MemoryOut])
def list_memories(status_filter: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Memory).where(Memory.user_id == current_user.id)
    if status_filter:
        stmt = stmt.where(Memory.status == status_filter)
    return list(db.scalars(stmt.order_by(Memory.updated_at.desc())).all())

@router.post("", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memory = Memory(user_id=current_user.id, **payload.model_dump())
    db.add(memory); db.commit(); db.refresh(memory)
    return memory

@router.patch("/{memory_id}", response_model=MemoryOut)
def update_memory(memory_id: str, payload: MemoryUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memory = owned_memory(db, current_user.id, memory_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(memory, key, value)
    db.commit(); db.refresh(memory)
    return memory

@router.post("/{memory_id}/confirm", response_model=MemoryOut)
def confirm_memory(memory_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memory = owned_memory(db, current_user.id, memory_id)
    # Approval is explicit: pending suggestions should not personalize answers.
    memory.status = "active"
    db.commit(); db.refresh(memory)
    return memory

@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memory = owned_memory(db, current_user.id, memory_id)
    db.delete(memory); db.commit()
    return None
