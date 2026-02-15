from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database, auth

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/pending-users", response_model=List[schemas.User])
def get_pending_users(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user)
):
    return db.query(models.User).filter(models.User.is_approved == False).all()

@router.post("/approve/{user_id}", response_model=schemas.User)
def approve_user(
    user_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_approved = True
    db.commit()
    db.refresh(user)
    return user
