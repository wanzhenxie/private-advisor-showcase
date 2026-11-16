from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, UsageEvent
from ..schemas import UsageOut

router = APIRouter(prefix="/api/usage", tags=["usage"])

@router.get("", response_model=UsageOut)
def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.input_tokens), 0),
            func.coalesce(func.sum(UsageEvent.output_tokens), 0),
            func.count(UsageEvent.id),
        ).where(UsageEvent.user_id == current_user.id)
    ).one()
    return UsageOut(
        input_tokens=int(row[0] or 0),
        output_tokens=int(row[1] or 0),
        calls=int(row[2] or 0),
    )
