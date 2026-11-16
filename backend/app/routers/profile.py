from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, Profile
from ..schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("", response_model=ProfileOut)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = current_user.profile
    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile); db.commit(); db.refresh(profile)
    return profile

@router.put("", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = current_user.profile or Profile(user_id=current_user.id)
    if profile.id is None:
        db.add(profile)
    profile.display_name = payload.display_name
    profile.locale = payload.locale
    profile.timezone = payload.timezone
    profile.advisor_preferences = payload.advisor_preferences
    db.commit(); db.refresh(profile)
    return profile
